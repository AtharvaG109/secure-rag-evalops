

def test_ingest_dir_reads_pdf_as_base64(tmp_path) -> None:
    from scripts.ingest_dir import _read_content

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"pdf-bytes")

    assert _read_content(pdf_path) == "cGRmLWJ5dGVz"


def test_ingest_dir_reads_source_code_as_text(tmp_path) -> None:
    from scripts.ingest_dir import _read_content

    source_path = tmp_path / "sample.py"
    source_path.write_text("print('hello')", encoding="utf-8")

    assert _read_content(source_path) == "print('hello')"


def test_ingest_dir_accepts_single_file_path(tmp_path) -> None:
    from typer.testing import CliRunner

    from scripts.ingest_dir import app

    source_path = tmp_path / "sample.py"
    source_path.write_text("print('hello')", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [str(source_path), "--namespace", "code", "--user-id", "demo-admin"],
    )

    assert result.exit_code == 0
    assert "failed" in result.stdout
