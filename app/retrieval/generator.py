from __future__ import annotations

import re

import httpx
from pydantic import BaseModel

from app.core.settings import settings
from app.retrieval.citations import INSUFFICIENT_CONTEXT_ANSWER
from app.tracing.trace import trace_span

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")
_CONTEXT_BLOCK_PATTERN = re.compile(r"(?ms)^\[(\d+)\]\s*(.*?)(?=^\[\d+\]\s|\Z)")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "for",
    "how",
    "in",
    "is",
    "of",
    "or",
    "the",
    "to",
    "what",
    "when",
    "which",
}
_QUERY_ALIASES = {
    "sev1": {"severity", "1"},
    "sev2": {"severity", "2"},
    "revoked": {"revocation"},
    "reviews": {"review"},
}


class GenerationResult(BaseModel):
    answer: str
    prompt_tokens: int
    completion_tokens: int


class ResponseGenerator:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._http_client = http_client

    async def generate(self, query: str, context: str) -> GenerationResult:
        async with trace_span("generation.generate"):
            if settings.GENERATION_PROVIDER == "ollama":
                return await self._generate_with_ollama(query, context)
            return self._generate(query, context)

    async def _generate_with_ollama(self, query: str, context: str) -> GenerationResult:
        client = self._http_client or httpx.AsyncClient(base_url=settings.OLLAMA_URL)
        should_close = self._http_client is None
        prompt = (
            "Answer using only the context. Cite every factual claim with [N]. "
            f"If context is insufficient, say: {INSUFFICIENT_CONTEXT_ANSWER}\n\n"
            f"Context:\n{context}\n\nQuestion: {query}"
        )
        try:
            response = await client.post(
                "/api/chat",
                json={
                    "model": settings.OLLAMA_CHAT_MODEL,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if should_close:
                await client.aclose()
        answer = str(payload["message"]["content"])
        return GenerationResult(
            answer=answer,
            prompt_tokens=int(payload.get("prompt_eval_count", 0)),
            completion_tokens=int(payload.get("eval_count", 0)),
        )

    def _generate(self, query: str, context: str) -> GenerationResult:
        query_tokens = self._meaningful_tokens(query)
        candidates = self._candidate_sentences(context)
        ranked = sorted(
            candidates,
            key=lambda candidate: (self._score_sentence(query_tokens, candidate[1]), -candidate[0]),
            reverse=True,
        )
        if not ranked or self._score_sentence(query_tokens, ranked[0][1]) == 0:
            answer = INSUFFICIENT_CONTEXT_ANSWER
        else:
            index, sentence = ranked[0]
            answer = f"{sentence} [{index}]"
        return GenerationResult(
            answer=answer,
            prompt_tokens=len(_TOKEN_PATTERN.findall(f"{context} {query}")),
            completion_tokens=len(_TOKEN_PATTERN.findall(answer)),
        )

    def _candidate_sentences(self, context: str) -> list[tuple[int, str]]:
        candidates: list[tuple[int, str]] = []
        for match in _CONTEXT_BLOCK_PATTERN.finditer(context):
            index = int(match.group(1))
            text = " ".join(
                line.strip()
                for line in match.group(2).splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
            for sentence in _SENTENCE_PATTERN.split(text):
                cleaned = sentence.strip()
                if cleaned:
                    candidates.append((index, cleaned))
        return candidates

    def _meaningful_tokens(self, text: str) -> set[str]:
        tokens = {token.lower() for token in _TOKEN_PATTERN.findall(text)} - _STOPWORDS
        expanded = set(tokens)
        for token in tokens:
            expanded.update(_QUERY_ALIASES.get(token, set()))
        return expanded

    def _score_sentence(self, query_tokens: set[str], sentence: str) -> int:
        sentence_tokens = self._meaningful_tokens(sentence)
        overlap = len(query_tokens & sentence_tokens)
        phrase_bonus = 2 if " ".join(sorted(query_tokens)) in sentence.lower() else 0
        return overlap + phrase_bonus
