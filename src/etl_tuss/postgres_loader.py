"""Carga idempotente de um Parquet de staging para o PostgreSQL (ADR 0007).

COPY das linhas para uma tabela temporária e upsert por (versao, tabela,
codigo), escrevendo só quando ``row_hash`` muda. Não cria schema: assume a
migration já aplicada.
"""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

_KEY_COLUMNS = ("versao", "tabela", "codigo")
_STAGING_TABLE = "_staging_carga"


@dataclass(frozen=True)
class UpsertResult:
    inserted: int
    updated: int
    unchanged: int

    def __add__(self, other: "UpsertResult") -> "UpsertResult":
        return UpsertResult(
            self.inserted + other.inserted,
            self.updated + other.updated,
            self.unchanged + other.unchanged,
        )


def load_parquet(
    conn: psycopg.Connection[TupleRow], parquet_path: Path, table: str
) -> UpsertResult:
    """Carrega um Parquet na tabela destino e relata inseridas/atualizadas/inalteradas."""
    return upsert_frame(conn, pl.read_parquet(parquet_path), table)


def upsert_frame(
    conn: psycopg.Connection[TupleRow], frame: pl.DataFrame, table: str
) -> UpsertResult:
    """Faz COPY do frame para staging e upsert idempotente na tabela destino."""
    with conn.cursor() as cur:
        _create_staging(cur, table)
        _copy_into_staging(cur, frame)
        inserted, updated = _upsert_from_staging(cur, table, frame.columns)
    conn.commit()
    return UpsertResult(inserted, updated, frame.height - inserted - updated)


def _create_staging(cur: psycopg.Cursor[TupleRow], table: str) -> None:
    cur.execute(
        sql.SQL("CREATE TEMP TABLE {staging} (LIKE {target}) ON COMMIT DROP").format(
            staging=sql.Identifier(_STAGING_TABLE),
            target=sql.Identifier(table),
        )
    )


def _copy_into_staging(cur: psycopg.Cursor[TupleRow], frame: pl.DataFrame) -> None:
    statement = sql.SQL("COPY {staging} ({cols}) FROM STDIN").format(
        staging=sql.Identifier(_STAGING_TABLE),
        cols=_identifiers(frame.columns),
    )
    with cur.copy(statement) as copy:
        for row in frame.iter_rows():
            copy.write_row(row)


def _upsert_from_staging(
    cur: psycopg.Cursor[TupleRow], table: str, columns: list[str]
) -> tuple[int, int]:
    row = cur.execute(_upsert_statement(table, columns)).fetchone()
    assert row is not None
    return int(row[0]), int(row[1])


def _upsert_statement(table: str, columns: list[str]) -> sql.Composed:
    updates = [name for name in columns if name not in _KEY_COLUMNS]
    return sql.SQL(
        "WITH upsert AS ("
        "INSERT INTO {target} ({cols}) SELECT {cols} FROM {staging} "
        "ON CONFLICT ({keys}) DO UPDATE SET {assignments} "
        "WHERE {target}.row_hash IS DISTINCT FROM EXCLUDED.row_hash "
        "RETURNING (xmax = 0) AS inserted"
        ") SELECT count(*) FILTER (WHERE inserted), "
        "count(*) FILTER (WHERE NOT inserted) FROM upsert"
    ).format(
        target=sql.Identifier(table),
        staging=sql.Identifier(_STAGING_TABLE),
        cols=_identifiers(columns),
        keys=_identifiers(_KEY_COLUMNS),
        assignments=sql.SQL(", ").join(_assignment(name) for name in updates),
    )


def _assignment(column: str) -> sql.Composed:
    return sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(column))


def _identifiers(columns: tuple[str, ...] | list[str]) -> sql.Composed:
    return sql.SQL(", ").join(sql.Identifier(name) for name in columns)
