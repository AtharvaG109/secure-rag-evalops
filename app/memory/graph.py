from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import (
    ChunkORM,
    DocumentORM,
    EntityMentionORM,
    EntityORM,
    EntityRelationORM,
    uuid_str,
)

if TYPE_CHECKING:
    from app.retrieval.retriever import ScoredChunk

_TITLE_PHRASE_PATTERN = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9+.#-]*|[A-Z]{2,})(?:[ \t]+(?:[A-Z][A-Za-z0-9+.#-]*|[0-9]+)){0,3}\b"
)
_IDENTIFIER_PATTERN = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_./:-]*\.(?:py|java|c|cpp|h|hpp|md|pdf|txt|json|ya?ml)\b"
)
_CAMEL_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9]+(?:[A-Z][A-Za-z0-9]+)+\b")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
_RELATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("uses", re.compile(r"\buses?\b", re.IGNORECASE)),
    ("depends_on", re.compile(r"\bdepends?\s+on\b", re.IGNORECASE)),
    ("connects_to", re.compile(r"\bconnects?\s+to\b", re.IGNORECASE)),
    ("stores", re.compile(r"\bstores?\b", re.IGNORECASE)),
    ("requires", re.compile(r"\brequires?\b", re.IGNORECASE)),
    ("calls", re.compile(r"\bcalls?\b", re.IGNORECASE)),
    ("imports", re.compile(r"\bimports?\b", re.IGNORECASE)),
    ("contains", re.compile(r"\bcontains?\b", re.IGNORECASE)),
)
_STOP_ENTITIES = {
    "A",
    "Add",
    "An",
    "And",
    "Check",
    "Choose",
    "Click",
    "Create",
    "Disable",
    "Enable",
    "Ensure",
    "Enter",
    "Explain",
    "False",
    "Find",
    "For",
    "From",
    "Go",
    "How",
    "If",
    "In",
    "It",
    "List",
    "None",
    "Save",
    "Scroll",
    "See",
    "Select",
    "Set",
    "Show",
    "The",
    "This",
    "To",
    "True",
    "Use",
    "What",
    "When",
    "Where",
    "Which",
    "With",
    "Why",
}
_MAX_ENTITY_NAME_LENGTH = 120


@dataclass(frozen=True)
class EntityCandidate:
    display_name: str
    normalized_name: str
    entity_type: str


@dataclass(frozen=True)
class EntityMatch:
    candidate: EntityCandidate
    start: int
    end: int


@dataclass(frozen=True)
class RelationCandidate:
    source_name: str
    target_name: str
    relation_type: str


def normalize_entity_name(name: str) -> str:
    return " ".join(name.lower().split())


def _candidate_type(name: str) -> str:
    if _IDENTIFIER_PATTERN.fullmatch(name):
        return "file"
    if "." in name or "/" in name:
        return "identifier"
    return "concept"


def extract_entities(text: str) -> list[EntityCandidate]:
    return [match.candidate for match in _entity_matches(text)]


def _entity_matches(text: str) -> list[EntityMatch]:
    found: dict[str, EntityMatch] = {}
    for pattern in (_IDENTIFIER_PATTERN, _CAMEL_PATTERN, _TITLE_PHRASE_PATTERN):
        for match in pattern.finditer(text):
            display_name = match.group(0).strip()
            if (
                display_name in _STOP_ENTITIES
                or len(display_name) < 2
                or len(display_name) > _MAX_ENTITY_NAME_LENGTH
                or _looks_like_noise(display_name)
            ):
                continue
            normalized_name = normalize_entity_name(display_name)
            found.setdefault(
                normalized_name,
                EntityMatch(
                    candidate=EntityCandidate(
                        display_name=display_name,
                        normalized_name=normalized_name,
                        entity_type=_candidate_type(display_name),
                    ),
                    start=match.start(),
                    end=match.end(),
                ),
            )
    return sorted(
        found.values(),
        key=lambda entity_match: (
            entity_match.start,
            entity_match.end,
            entity_match.candidate.display_name.lower(),
        ),
    )


def _looks_like_noise(name: str) -> bool:
    compact = name.replace(" ", "")
    parts = name.split()
    if all(part in _STOP_ENTITIES for part in name.split()):
        return True
    if len(parts) > 1 and parts[0] in _STOP_ENTITIES:
        return True
    if " " not in name and len(compact) > 40 and compact.isalnum():
        return True
    return False


def extract_relations(text: str) -> list[RelationCandidate]:
    relations: list[RelationCandidate] = []
    for sentence in _SENTENCE_SPLIT_PATTERN.split(text):
        entity_matches = _entity_matches(sentence)
        if len(entity_matches) < 2:
            continue
        for relation_type, pattern in _RELATION_PATTERNS:
            relation_match = pattern.search(sentence)
            if relation_match is None:
                continue
            before = [match for match in entity_matches if match.end <= relation_match.start()]
            after = [match for match in entity_matches if match.start >= relation_match.end()]
            if before and after:
                source = max(before, key=lambda match: match.end).candidate
                target = min(after, key=lambda match: match.start).candidate
            else:
                source = entity_matches[0].candidate
                target = entity_matches[1].candidate
            if source.normalized_name == target.normalized_name:
                break
            relations.append(
                RelationCandidate(
                    source_name=source.normalized_name,
                    target_name=target.normalized_name,
                    relation_type=relation_type,
                )
            )
            break
    return relations


class GraphMemory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def index_document(
        self,
        document: DocumentORM,
        chunks: list[ChunkORM],
    ) -> None:
        chunk_entities = {chunk.id: extract_entities(chunk.text) for chunk in chunks}
        chunk_relations = {chunk.id: extract_relations(chunk.text) for chunk in chunks}
        candidates = {
            candidate.normalized_name: candidate
            for entities in chunk_entities.values()
            for candidate in entities
        }
        if not candidates:
            return
        entity_cache = {
            entity.normalized_name: entity
            for entity in list(
                await self._session.scalars(
                    select(EntityORM).where(
                        EntityORM.namespace == document.namespace,
                        EntityORM.normalized_name.in_(candidates),
                    )
                )
            )
        }
        for normalized_name, candidate in candidates.items():
            if normalized_name in entity_cache:
                continue
            entity = EntityORM(
                id=uuid_str(),
                namespace=document.namespace,
                normalized_name=candidate.normalized_name,
                display_name=candidate.display_name,
                entity_type=candidate.entity_type,
            )
            self._session.add(entity)
            entity_cache[normalized_name] = entity

        for chunk in chunks:
            for candidate in chunk_entities[chunk.id]:
                entity = entity_cache[candidate.normalized_name]
                self._session.add(
                    EntityMentionORM(
                        entity_id=entity.id,
                        document_id=document.id,
                        chunk_id=chunk.id,
                        mention_text=candidate.display_name,
                    )
                )
            seen_relations: set[tuple[str, str, str]] = set()
            for relation in chunk_relations[chunk.id]:
                relation_key = (
                    relation.source_name,
                    relation.target_name,
                    relation.relation_type,
                )
                if relation_key in seen_relations:
                    continue
                seen_relations.add(relation_key)
                source = entity_cache.get(relation.source_name)
                target = entity_cache.get(relation.target_name)
                if source is None or target is None or source.id == target.id:
                    continue
                self._session.add(
                    EntityRelationORM(
                        namespace=document.namespace,
                        source_entity_id=source.id,
                        target_entity_id=target.id,
                        relation_type=relation.relation_type,
                        evidence_chunk_id=chunk.id,
                        confidence=1.0,
                    )
                )

    async def graph_search(
        self,
        query: str,
        namespace: str,
        top_k: int,
    ) -> list[ScoredChunk]:
        from app.retrieval.retriever import ScoredChunk

        query_names = [candidate.normalized_name for candidate in extract_entities(query)]
        if not query_names:
            return []
        entities = list(
            await self._session.scalars(
                select(EntityORM).where(
                    EntityORM.namespace == namespace,
                    EntityORM.normalized_name.in_(query_names),
                )
            )
        )
        if not entities:
            return []
        seed_ids = {entity.id for entity in entities}
        relations = list(
            await self._session.scalars(
                select(EntityRelationORM).where(
                    EntityRelationORM.namespace == namespace,
                    or_(
                        EntityRelationORM.source_entity_id.in_(seed_ids),
                        EntityRelationORM.target_entity_id.in_(seed_ids),
                    ),
                )
            )
        )
        related_ids = set(seed_ids)
        evidence_chunk_ids: set[str] = set()
        for relation in relations:
            related_ids.add(relation.source_entity_id)
            related_ids.add(relation.target_entity_id)
            evidence_chunk_ids.add(relation.evidence_chunk_id)

        rows = list(
            await self._session.execute(
                select(ChunkORM, DocumentORM, EntityMentionORM.entity_id)
                .join(DocumentORM, ChunkORM.document_id == DocumentORM.id)
                .join(EntityMentionORM, EntityMentionORM.chunk_id == ChunkORM.id)
                .where(
                    DocumentORM.namespace == namespace,
                    EntityMentionORM.entity_id.in_(related_ids),
                )
            )
        )
        mention_counts = Counter(chunk.id for chunk, _, _ in rows)
        chunks: dict[str, ScoredChunk] = {}
        for chunk, document, _ in rows:
            score = 0.35 + 0.15 * mention_counts[chunk.id]
            if chunk.id in evidence_chunk_ids:
                score += 0.35
            chunks[chunk.id] = ScoredChunk(
                chunk_id=chunk.id,
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                score=score,
                namespace=document.namespace,
                source_filename=document.source_filename,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
        return sorted(chunks.values(), key=lambda chunk: chunk.score, reverse=True)[:top_k]


def merge_graph_chunks(
    existing_chunks: Iterable[ScoredChunk],
    graph_chunks: Iterable[ScoredChunk],
    top_k: int,
) -> list[ScoredChunk]:
    combined: dict[tuple[str, int | None], ScoredChunk] = {}
    for chunk in existing_chunks:
        combined[(chunk.document_id, chunk.chunk_index)] = chunk
    for chunk in graph_chunks:
        key = (chunk.document_id, chunk.chunk_index)
        current = combined.get(key)
        if current is None:
            combined[key] = chunk
            continue
        combined[key] = current.model_copy(update={"score": current.score + chunk.score})
    return sorted(combined.values(), key=lambda chunk: chunk.score, reverse=True)[:top_k]
