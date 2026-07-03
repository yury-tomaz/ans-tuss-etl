import os
from pathlib import Path

import psycopg
import xlsxwriter
from psycopg.rows import TupleRow

from etl_tuss.cli import main

_CORE_HEADER = [
    "Código do Termo",
    "Termo",
    "Data de início de vigência",
    "Data de fim de vigência",
    "Data de fim de implantação",
]
_DEFAULT_DSN = "postgres://tuss:tuss@localhost:5432/tuss"


def _write_release(root: Path) -> Path:
    root.mkdir()
    path = root / "TUSS 18 - DIÁRIAS.xlsx"
    workbook = xlsxwriter.Workbook(str(path))
    workbook.add_worksheet("Capa")
    sheet = workbook.add_worksheet("Tab 18")
    sheet.write(0, 0, "Tabela 18")
    for col, label in enumerate(_CORE_HEADER):
        sheet.write(2, col, label)
    for offset, codigo in enumerate(("011", "012")):
        sheet.write_string(3 + offset, 0, codigo)
        sheet.write(3 + offset, 1, "TERMO")
        sheet.write(3 + offset, 2, "2012-10-10")
    workbook.close()
    return root


def _test_dsn() -> str:
    return os.environ.get("TUSS_TEST_DSN", _DEFAULT_DSN)


def test_main_extracts_and_loads(conn: psycopg.Connection[TupleRow], tmp_path: Path) -> None:
    release = _write_release(tmp_path / "release")
    staging = tmp_path / "staging"
    code = main([str(release), "202601", "--staging", str(staging), "--dsn", _test_dsn()])
    assert code == 0
    row = conn.execute("SELECT count(*) FROM tuss_termo").fetchone()
    assert row is not None
    assert row[0] == 2


def test_main_writes_staging_parquet(conn: psycopg.Connection[TupleRow], tmp_path: Path) -> None:
    release = _write_release(tmp_path / "release")
    staging = tmp_path / "staging"
    main([str(release), "202601", "--staging", str(staging), "--dsn", _test_dsn()])
    assert (staging / "versao=202601" / "tab_18.parquet").exists()
