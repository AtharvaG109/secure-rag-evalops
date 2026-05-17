import pytest

from app.tracing.trace import create_trace_id, get_trace_id, trace_span


def test_trace_id_creation_and_retrieval() -> None:
    trace_id = create_trace_id()
    assert get_trace_id() == trace_id


@pytest.mark.asyncio
async def test_trace_span_runs_without_error() -> None:
    async with trace_span("demo"):
        assert get_trace_id() != ""


@pytest.mark.asyncio
async def test_trace_span_logs_errors() -> None:
    with pytest.raises(RuntimeError):
        async with trace_span("demo"):
            raise RuntimeError("boom")
