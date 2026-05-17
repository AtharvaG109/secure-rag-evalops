from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orm import CostEventORM
from app.core.schemas import CostRecord
from app.core.settings import settings


class CostTracker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def compute_chat_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * settings.CHAT_INPUT_PRICE_PER_1M
            + completion_tokens * settings.CHAT_OUTPUT_PRICE_PER_1M
        ) / 1_000_000

    def compute_embedding_cost(self, token_count: int) -> float:
        return token_count * settings.EMBEDDING_PRICE_PER_1M / 1_000_000

    async def record(
        self,
        trace_id: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        embedding_tokens: int = 0,
    ) -> CostRecord:
        chat_cost = self.compute_chat_cost(prompt_tokens, completion_tokens)
        embedding_cost = self.compute_embedding_cost(embedding_tokens)
        event = CostEventORM(
            trace_id=trace_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            embedding_tokens=embedding_tokens,
            chat_cost_usd=chat_cost,
            embedding_cost_usd=embedding_cost,
            total_cost_usd=chat_cost + embedding_cost,
        )
        self._session.add(event)
        await self._session.commit()
        return CostRecord.model_validate(event)
