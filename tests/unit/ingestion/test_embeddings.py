import pytest

from app.ingestion.embeddings import EmbeddingClient


@pytest.mark.asyncio
async def test_embedding_client_returns_deterministic_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.ingestion.embeddings.settings.EMBEDDING_DIMENSIONS", 8)
    client = EmbeddingClient()

    first = await client.embed_batch(["hello world"])
    second = await client.embed_batch(["hello world"])

    assert len(first[0]) == 8
    assert first == second


@pytest.mark.asyncio
async def test_embedding_client_distinguishes_different_texts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.ingestion.embeddings.settings.EMBEDDING_DIMENSIONS", 8)
    client = EmbeddingClient()

    first, second = await client.embed_batch(["hello world", "security policy"])

    assert first != second


@pytest.mark.asyncio
async def test_embedding_client_rejects_batches_over_limit() -> None:
    client = EmbeddingClient()

    with pytest.raises(ValueError, match="batch size"):
        await client.embed_batch(["text"] * 101)


@pytest.mark.asyncio
async def test_embedding_client_can_use_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    monkeypatch.setattr("app.ingestion.embeddings.settings.EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setattr("app.ingestion.embeddings.settings.EMBEDDING_DIMENSIONS", 2)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://ollama") as client:
        result = await EmbeddingClient(client).embed_batch(["hello"])

    assert result == [[0.1, 0.2]]
