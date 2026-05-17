from pathlib import Path

import pytest

from app.evaluation.dataset import load_jsonl_dataset


def test_jsonl_loader_parses_ten_samples() -> None:
    assert len(load_jsonl_dataset("evals/golden_set.jsonl")) == 10


def test_jsonl_loader_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"query":"ok"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 1"):
        load_jsonl_dataset(str(path))
