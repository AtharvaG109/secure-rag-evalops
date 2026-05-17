from __future__ import annotations

import base64
import json
from typing import Any

import fitz  # type: ignore[import-untyped]  # PyMuPDF does not ship typing metadata.
from pydantic import BaseModel


class ParsedPage(BaseModel):
    text: str
    page_number: int


def parse_pdf_bytes(content: bytes) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    with fitz.open(stream=content, filetype="pdf") as document:
        for page_number, page in enumerate(document, start=1):
            pages.append(ParsedPage(text=page.get_text(), page_number=page_number))
    return pages


def _decode_text(content: bytes | str) -> str:
    return content.decode("utf-8") if isinstance(content, bytes) else content


def parse_text(content: bytes | str, source_filename: str = "") -> list[ParsedPage]:
    _ = source_filename
    return [ParsedPage(text=_decode_text(content), page_number=1)]


def _flatten_json(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(_flatten_json(child, child_prefix))
        return lines
    if isinstance(value, list):
        lines = []
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            lines.extend(_flatten_json(child, child_prefix))
        return lines
    return [f"{prefix}: {value}"]


def parse_json(content: bytes | str) -> list[ParsedPage]:
    parsed = json.loads(_decode_text(content))
    return [ParsedPage(text="\n".join(_flatten_json(parsed)), page_number=1)]


def parse_file(
    content: bytes | str,
    source_type: str,
    source_filename: str = "",
) -> list[ParsedPage]:
    normalized_type = source_type.lower().lstrip(".")
    if normalized_type == "pdf":
        pdf_content = base64.b64decode(content) if isinstance(content, str) else content
        return parse_pdf_bytes(pdf_content)
    text_types = {"txt", "md", "markdown", "py", "c", "cpp", "cc", "cxx", "java", "h", "hpp"}
    if normalized_type in text_types:
        return parse_text(content, source_filename)
    if normalized_type == "json":
        return parse_json(content)
    raise ValueError(f"unsupported source type: {source_type}")
