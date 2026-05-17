import pytest

from app.ingestion.parsers import parse_file, parse_json, parse_text


def test_markdown_headings_are_preserved() -> None:
    pages = parse_text("# Heading\nBody", "policy.md")
    assert pages[0].text.startswith("# Heading")


def test_json_is_flattened() -> None:
    pages = parse_json('{"policy":{"mfa":true},"tiers":["sev1"]}')
    assert "policy.mfa: True" in pages[0].text
    assert "tiers[0]: sev1" in pages[0].text


def test_unsupported_source_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported source type"):
        parse_file("hello", "docx")


def test_source_code_extensions_are_parsed_as_text() -> None:
    for source_type in ["py", "c", "cpp", "cc", "cxx", "java", "h", "hpp"]:
        pages = parse_file("int main() { return 0; }", source_type)
        assert pages[0].text == "int main() { return 0; }"
