from typing import Any

import pytest

from app.tracing.cost_tracker import CostTracker


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, item: Any) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_cost_uses_settings_values_and_persists() -> None:
    session = FakeSession()
    tracker = CostTracker(session)  # type: ignore[arg-type]

    record = await tracker.record(
        "trace",
        "chat",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    assert record.chat_cost_usd == 0.0
    assert record.total_cost_usd == 0.0
    assert session.added
