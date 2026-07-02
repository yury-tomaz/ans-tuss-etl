from datetime import date
from pathlib import Path

import polars as pl
from polars.testing import assert_frame_equal

from etl_tuss.parquet_writer import write_staging_parquet

_SCHEMA = {
    "versao": pl.String,
    "tabela": pl.String,
    "codigo": pl.String,
    "termo": pl.String,
    "descricao": pl.String,
    "inicio_vigencia": pl.Date,
    "fim_vigencia": pl.Date,
    "fim_implantacao": pl.Date,
    "row_hash": pl.String,
}


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "versao": ["202601", "202601"],
            "tabela": ["23", "23"],
            "codigo": ["01", "02"],
            "termo": ["Eletivo", "Urgência"],
            "descricao": [None, None],
            "inicio_vigencia": [date(2012, 10, 10), date(2012, 10, 10)],
            "fim_vigencia": [None, None],
            "fim_implantacao": [date(2014, 8, 31), None],
            "row_hash": ["aaa", "bbb"],
        },
        schema=_SCHEMA,
    )


def test_writes_to_hive_path(tmp_path: Path) -> None:
    path = write_staging_parquet(_frame(), tmp_path, "202601", "23")
    assert path == tmp_path / "versao=202601" / "tab_23.parquet"
    assert path.exists()


def test_creates_missing_directory(tmp_path: Path) -> None:
    staging_root = tmp_path / "staging"
    path = write_staging_parquet(_frame(), staging_root, "202601", "23")
    assert path.exists()


def test_round_trip_preserves_frame(tmp_path: Path) -> None:
    path = write_staging_parquet(_frame(), tmp_path, "202601", "23")
    assert_frame_equal(pl.read_parquet(path), _frame())


def test_overwrite_is_idempotent(tmp_path: Path) -> None:
    write_staging_parquet(_frame(), tmp_path, "202601", "23")
    path = write_staging_parquet(_frame(), tmp_path, "202601", "23")
    parquets = list((tmp_path / "versao=202601").glob("*.parquet"))
    assert parquets == [path]
    assert_frame_equal(pl.read_parquet(path), _frame())
