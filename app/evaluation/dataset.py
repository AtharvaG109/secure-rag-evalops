from __future__ import annotations

import json

from pydantic import ValidationError

from app.core.schemas import EvalSample


def load_jsonl_dataset(path: str) -> list[EvalSample]:
    samples: list[EvalSample] = []
    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                payload = json.loads(line)
                samples.append(EvalSample.model_validate(payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"invalid dataset line {line_number}") from exc
    return samples
