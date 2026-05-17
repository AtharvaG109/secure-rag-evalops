from pathlib import Path

from app.evaluation.dataset import load_jsonl_dataset


def test_demo_corpus_files_exist_and_are_long_enough() -> None:
    files = list(Path("demo_corpus").glob("*.md"))
    assert len(files) == 5
    assert all(len(path.read_text(encoding="utf-8").split()) >= 400 for path in files)


def test_golden_set_has_ten_samples() -> None:
    assert len(load_jsonl_dataset("evals/golden_set.jsonl")) == 10
