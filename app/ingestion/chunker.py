from __future__ import annotations

import re

import tiktoken
from pydantic import BaseModel

from app.ingestion.parsers import ParsedPage

_CODE_TYPES = {"py", "c", "cpp", "cc", "cxx", "java", "h", "hpp"}
_CODE_BOUNDARY = re.compile(
    r"^\s*(?:async\s+def|def|class|(?:public|private|protected)?\s*(?:static\s+)?[A-Za-z_][\w:<>,\[\]\s*&]*\s+[A-Za-z_]\w*\s*\(|[A-Za-z_]\w*\s*\([^;]*\)\s*\{)"
)


class ChunkCandidate(BaseModel):
    text: str
    chunk_index: int
    token_count: int
    page_start: int
    page_end: int


def _split_prose(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]


def _split_code(text: str) -> list[str]:
    segments: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if current and _CODE_BOUNDARY.match(line):
            segments.append("\n".join(current).strip())
            current = []
        current.append(line)
    if current:
        segments.append("\n".join(current).strip())
    return [segment for segment in segments if segment]


def _window_tokens(tokens: list[int], chunk_size: int, chunk_overlap: int) -> list[list[int]]:
    windows: list[list[int]] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        windows.append(tokens[start:end])
        if end == len(tokens):
            break
        start = end - chunk_overlap
    return windows


def _page_segments(page: ParsedPage, source_type: str) -> list[str]:
    if source_type.lower().lstrip(".") in _CODE_TYPES:
        return _split_code(page.text)
    return _split_prose(page.text)


def chunk_pages(
    pages: list[ParsedPage],
    chunk_size: int,
    chunk_overlap: int,
    encoding_name: str = "cl100k_base",
    source_type: str = "txt",
) -> list[ChunkCandidate]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size - 1")
    if not pages:
        return []

    encoding = tiktoken.get_encoding(encoding_name)
    chunks: list[ChunkCandidate] = []
    chunk_index = 0

    for page in pages:
        buffer_tokens: list[int] = []
        for segment in _page_segments(page, source_type):
            segment_tokens = encoding.encode(segment)
            if len(segment_tokens) > chunk_size:
                if buffer_tokens:
                    chunks.append(
                        ChunkCandidate(
                            text=encoding.decode(buffer_tokens).strip(),
                            chunk_index=chunk_index,
                            token_count=len(buffer_tokens),
                            page_start=page.page_number,
                            page_end=page.page_number,
                        )
                    )
                    chunk_index += 1
                    buffer_tokens = []
                for window in _window_tokens(segment_tokens, chunk_size, chunk_overlap):
                    chunks.append(
                        ChunkCandidate(
                            text=encoding.decode(window).strip(),
                            chunk_index=chunk_index,
                            token_count=len(window),
                            page_start=page.page_number,
                            page_end=page.page_number,
                        )
                    )
                    chunk_index += 1
                continue
            separator_tokens = encoding.encode("\n\n") if buffer_tokens else []
            next_size = len(buffer_tokens) + len(separator_tokens) + len(segment_tokens)
            if buffer_tokens and next_size > chunk_size:
                chunks.append(
                    ChunkCandidate(
                        text=encoding.decode(buffer_tokens).strip(),
                        chunk_index=chunk_index,
                        token_count=len(buffer_tokens),
                        page_start=page.page_number,
                        page_end=page.page_number,
                    )
                )
                chunk_index += 1
                overlap = buffer_tokens[-chunk_overlap:] if chunk_overlap else []
                buffer_tokens = overlap + (encoding.encode("\n\n") if overlap else [])
            buffer_tokens.extend(separator_tokens if not buffer_tokens else [])
            buffer_tokens.extend(segment_tokens)
        if buffer_tokens:
            chunks.append(
                ChunkCandidate(
                    text=encoding.decode(buffer_tokens).strip(),
                    chunk_index=chunk_index,
                    token_count=len(buffer_tokens),
                    page_start=page.page_number,
                    page_end=page.page_number,
                )
            )
            chunk_index += 1
    return chunks
