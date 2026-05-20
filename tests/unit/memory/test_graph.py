from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from app.core.orm import ChunkORM, DocumentORM, EntityORM, EntityRelationORM
from app.memory.graph import (
    GraphMemory,
    extract_entities,
    extract_relations,
    merge_graph_chunks,
)
from app.retrieval.retriever import ScoredChunk


def test_extract_entities_finds_concepts_and_files() -> None:
    entities = extract_entities("PaymentService uses PostgreSQL in billing.py.")

    assert {entity.normalized_name for entity in entities} >= {
        "paymentservice",
        "postgresql",
        "billing.py",
    }


def test_extract_relations_finds_supported_relation_verbs() -> None:
    relations = extract_relations("PaymentService uses PostgreSQL.")

    assert relations[0].source_name == "paymentservice"
    assert relations[0].target_name == "postgresql"
    assert relations[0].relation_type == "uses"


def test_extract_relations_prefers_entities_around_relation_verb() -> None:
    relations = extract_relations("PaymentService uses PostgreSQL in billing.py.")

    assert relations[0].source_name == "paymentservice"
    assert relations[0].target_name == "postgresql"


def test_extract_entities_skips_prompt_leading_question_words() -> None:
    entities = extract_entities("Explain PaymentService")

    assert {entity.normalized_name for entity in entities} == {"paymentservice"}


def test_extract_entities_skips_overlong_noise() -> None:
    entities = extract_entities("A" * 180)

    assert entities == []


def test_extract_entities_do_not_cross_line_breaks() -> None:
    entities = extract_entities("IceScraper\n\t\t6")

    assert {entity.display_name for entity in entities} == {"IceScraper"}


def test_extract_entities_skips_common_instruction_words() -> None:
    entities = extract_entities("Click Save and Select Enable.")

    assert entities == []


class FakeScalarResult:
    def __init__(self, values: Iterable[Any]) -> None:
        self._values = list(values)

    def __iter__(self):
        return iter(self._values)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.scalar_calls = 0
        self.scalars_calls = 0
        self.graph_entities = [
            EntityORM(
                id="entity-payment",
                namespace="code",
                normalized_name="paymentservice",
                display_name="PaymentService",
                entity_type="concept",
            )
        ]
        self.relations = [
            EntityRelationORM(
                id="relation-1",
                namespace="code",
                source_entity_id="entity-payment",
                target_entity_id="entity-postgres",
                relation_type="uses",
                evidence_chunk_id="chunk-2",
                confidence=1.0,
            )
        ]
        self.rows = [
            (
                ChunkORM(
                    id="chunk-1",
                    document_id="doc-1",
                    text="PaymentService is documented here.",
                    chunk_index=0,
                    token_count=4,
                    page_start=1,
                    page_end=1,
                ),
                DocumentORM(
                    id="doc-1",
                    namespace="code",
                    source_type="py",
                    source_filename="service.py",
                    file_hash="hash-1",
                    metadata_json={},
                ),
                "entity-payment",
            ),
            (
                ChunkORM(
                    id="chunk-2",
                    document_id="doc-2",
                    text="PaymentService uses PostgreSQL.",
                    chunk_index=0,
                    token_count=4,
                    page_start=1,
                    page_end=1,
                ),
                DocumentORM(
                    id="doc-2",
                    namespace="code",
                    source_type="md",
                    source_filename="architecture.md",
                    file_hash="hash-2",
                    metadata_json={},
                ),
                "entity-postgres",
            ),
        ]

    async def scalar(self, _: object) -> EntityORM | None:
        self.scalar_calls += 1
        return None

    async def scalars(self, _: object) -> FakeScalarResult:
        self.scalars_calls += 1
        if self.scalars_calls == 1:
            return FakeScalarResult(self.graph_entities)
        if self.scalars_calls == 2:
            return FakeScalarResult(self.relations)
        return FakeScalarResult([])

    async def execute(self, _: object) -> list[tuple[ChunkORM, DocumentORM, str]]:
        return self.rows

    def add(self, item: Any) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        for item in self.added:
            if isinstance(item, EntityORM) and not item.id:
                item.id = f"entity-{len(self.added)}"


@pytest.mark.asyncio
async def test_graph_indexing_adds_mentions_and_relations() -> None:
    session = FakeSession()
    document = DocumentORM(
        id="doc-1",
        namespace="code",
        source_type="py",
        source_filename="service.py",
        file_hash="hash",
        metadata_json={},
    )
    chunk = ChunkORM(
        id="chunk-1",
        document_id="doc-1",
        text="PaymentService uses PostgreSQL.",
        chunk_index=0,
        token_count=4,
        page_start=1,
        page_end=1,
    )

    await GraphMemory(session).index_document(document, [chunk])  # type: ignore[arg-type]

    assert any(item.__class__.__name__ == "EntityMentionORM" for item in session.added)
    assert any(item.__class__.__name__ == "EntityRelationORM" for item in session.added)


@pytest.mark.asyncio
async def test_graph_indexing_deduplicates_repeated_relations_per_chunk() -> None:
    session = FakeSession()
    document = DocumentORM(
        id="doc-1",
        namespace="code",
        source_type="py",
        source_filename="service.py",
        file_hash="hash",
        metadata_json={},
    )
    chunk = ChunkORM(
        id="chunk-1",
        document_id="doc-1",
        text="PaymentService uses PostgreSQL. PaymentService uses PostgreSQL.",
        chunk_index=0,
        token_count=8,
        page_start=1,
        page_end=1,
    )

    await GraphMemory(session).index_document(document, [chunk])  # type: ignore[arg-type]

    relation_count = sum(item.__class__.__name__ == "EntityRelationORM" for item in session.added)
    assert relation_count == 1


@pytest.mark.asyncio
async def test_graph_search_boosts_relation_evidence_chunks() -> None:
    session = FakeSession()

    chunks = await GraphMemory(session).graph_search("Explain PaymentService", "code", 5)  # type: ignore[arg-type]

    assert chunks[0].chunk_id == "chunk-2"
    assert chunks[0].score > chunks[1].score


def test_merge_graph_chunks_adds_score_to_existing_result() -> None:
    merged = merge_graph_chunks(
        [
            ScoredChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                chunk_index=0,
                text="PaymentService",
                score=0.5,
                namespace="code",
                source_filename="service.py",
                page_start=1,
                page_end=1,
            )
        ],
        [
            ScoredChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                chunk_index=0,
                text="PaymentService",
                score=0.4,
                namespace="code",
                source_filename="service.py",
                page_start=1,
                page_end=1,
            )
        ],
        5,
    )

    assert merged[0].score == 0.9
