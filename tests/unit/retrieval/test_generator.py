import pytest

from app.retrieval.citations import INSUFFICIENT_CONTEXT_ANSWER
from app.retrieval.generator import ResponseGenerator


@pytest.mark.asyncio
async def test_generator_extracts_answer_from_context_with_citation() -> None:
    generator = ResponseGenerator()

    result = await generator.generate(
        "Is MFA required?",
        (
            "[1] MFA is required for all corporate systems.\n\n"
            "[2] Financial records are retained for 7 years."
        ),
    )

    assert result.answer == "MFA is required for all corporate systems. [1]"
    assert result.prompt_tokens > 0
    assert result.completion_tokens > 0


@pytest.mark.asyncio
async def test_generator_uses_one_based_context_citation() -> None:
    generator = ResponseGenerator()

    result = await generator.generate(
        "What protects data at rest?",
        "[1] MFA is required for all corporate systems.\n\n[2] Data at rest must use AES-256.",
    )

    assert result.answer == "Data at rest must use AES-256. [2]"


@pytest.mark.asyncio
async def test_generator_abstains_when_context_is_not_relevant() -> None:
    generator = ResponseGenerator()

    result = await generator.generate("What is the retention period?", "[1] MFA is required.")

    assert result.answer == INSUFFICIENT_CONTEXT_ANSWER


@pytest.mark.asyncio
async def test_generator_reads_multiline_context_blocks() -> None:
    generator = ResponseGenerator()

    result = await generator.generate(
        "Which vendors require SOC 2 Type II?",
        (
            "[1] # Vendor Security Policy\n\n"
            "Critical vendors require SOC 2 Type II evidence before onboarding.\n\n"
            "[2] Vendor relationships require monitoring."
        ),
    )

    assert result.answer == "Critical vendors require SOC 2 Type II evidence before onboarding. [1]"


@pytest.mark.asyncio
async def test_generator_can_use_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    monkeypatch.setattr("app.retrieval.generator.settings.GENERATION_PROVIDER", "ollama")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "message": {"content": "MFA is required [1]."},
                "prompt_eval_count": 10,
                "eval_count": 4,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://ollama") as client:
        result = await ResponseGenerator(client).generate(
            "Is MFA required?",
            "[1] MFA is required.",
        )

    assert result.answer == "MFA is required [1]."
    assert result.prompt_tokens == 10
