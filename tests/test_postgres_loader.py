from datetime import date
from pathlib import Path

import polars as pl
import psycopg
from psycopg.rows import TupleRow

from etl_tuss.postgres_loader import UpsertResult, load_parquet, upsert_frame

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


def _termo_frame(termo: str, row_hash: str) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "versao": ["202601"],
            "tabela": ["18"],
            "codigo": ["011"],
            "termo": [termo],
            "descricao": [None],
            "inicio_vigencia": [date(2012, 10, 10)],
            "fim_vigencia": [None],
            "fim_implantacao": [None],
            "row_hash": [row_hash],
        },
        schema=_SCHEMA,
    )


def _count(conn: psycopg.Connection[TupleRow]) -> int:
    row = conn.execute("SELECT count(*) FROM tuss_termo").fetchone()
    assert row is not None
    return int(row[0])


def test_upsert_inserts_new_rows(conn: psycopg.Connection[TupleRow]) -> None:
    result = upsert_frame(conn, _termo_frame("ALFA", "hash-a"), "tuss_termo")
    assert result == UpsertResult(inserted=1, updated=0, unchanged=0)
    assert _count(conn) == 1


def test_upsert_is_idempotent(conn: psycopg.Connection[TupleRow]) -> None:
    upsert_frame(conn, _termo_frame("ALFA", "hash-a"), "tuss_termo")
    result = upsert_frame(conn, _termo_frame("ALFA", "hash-a"), "tuss_termo")
    assert result == UpsertResult(inserted=0, updated=0, unchanged=1)
    assert _count(conn) == 1


def test_upsert_updates_changed_row(conn: psycopg.Connection[TupleRow]) -> None:
    upsert_frame(conn, _termo_frame("ALFA", "hash-a"), "tuss_termo")
    result = upsert_frame(conn, _termo_frame("ALFA CORRIGIDO", "hash-b"), "tuss_termo")
    assert result == UpsertResult(inserted=0, updated=1, unchanged=0)
    row = conn.execute("SELECT termo FROM tuss_termo WHERE codigo = '011'").fetchone()
    assert row is not None
    assert row[0] == "ALFA CORRIGIDO"


def test_load_parquet_reads_and_upserts(conn: psycopg.Connection[TupleRow], tmp_path: Path) -> None:
    parquet = tmp_path / "tab_18.parquet"
    _termo_frame("ALFA", "hash-a").write_parquet(parquet)
    result = load_parquet(conn, parquet, "tuss_termo")
    assert result == UpsertResult(inserted=1, updated=0, unchanged=0)
    assert _count(conn) == 1
