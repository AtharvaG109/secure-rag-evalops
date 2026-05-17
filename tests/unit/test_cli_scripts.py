from scripts.ingest_dir import app as ingest_app
from scripts.query import app as query_app
from scripts.run_eval import app as eval_app


def test_cli_modules_expose_typer_apps() -> None:
    assert ingest_app is not None
    assert query_app is not None
    assert eval_app is not None
