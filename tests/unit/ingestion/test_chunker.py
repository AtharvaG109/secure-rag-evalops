from app.ingestion.chunker import chunk_pages
from app.ingestion.parsers import ParsedPage


def test_chunker_respects_token_budget() -> None:
    chunks = chunk_pages(
        [ParsedPage(text="word " * 200, page_number=1)],
        chunk_size=32,
        chunk_overlap=4,
    )
    assert chunks
    assert all(chunk.token_count <= 32 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunker_keeps_code_boundaries_when_possible() -> None:
    chunks = chunk_pages(
        [
            ParsedPage(
                text="def alpha():\n    return 1\n\ndef beta():\n    return 2",
                page_number=1,
            )
        ],
        chunk_size=10,
        chunk_overlap=0,
        source_type="py",
    )

    assert chunks[0].text.startswith("def alpha")
    assert chunks[1].text.startswith("def beta")


def test_chunker_prefers_paragraph_boundaries_for_long_text() -> None:
    chunks = chunk_pages(
        [ParsedPage(text="alpha paragraph.\n\nbeta paragraph.", page_number=1)],
        chunk_size=6,
        chunk_overlap=0,
    )

    assert chunks[0].text == "alpha paragraph."
    assert chunks[1].text == "beta paragraph."
