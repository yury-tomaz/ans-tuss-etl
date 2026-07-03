"""Carga idempotente de um Parquet de staging para o PostgreSQL (ADR 0007).

COPY das linhas para uma tabela temporária e upsert por (versao, tabela,
codigo), escrevendo só quando ``row_hash`` muda. Não cria schema: assume a
migration já aplicada.
"""

from pathlib import Path

import polars as pl
import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

_KEY_COLUMNS = ("versao", "tabela", "codigo")
_STAGING_TABLE = "_staging_carga"


def load_parquet(conn: psycopg.Connection[TupleRow], parquet_path: Path, table: str) -> int:
    """Carrega um Parquet na tabela destino e devolve o número de linhas afetadas."""
    return upsert_frame(conn, pl.read_parquet(parquet_path), table)


def upsert_frame(conn: psycopg.Connection[TupleRow], frame: pl.DataFrame, table: str) -> int:
    """Faz COPY do frame para staging e upsert idempotente na tabela destino."""
    with conn.cursor() as cur:
        _create_staging(cur, table)
        _copy_into_staging(cur, frame)
        affected = _upsert_from_staging(cur, table, frame.columns)
    conn.commit()
    return affected


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


def _upsert_from_staging(cur: psycopg.Cursor[TupleRow], table: str, columns: list[str]) -> int:
    updates = [name for name in columns if name not in _KEY_COLUMNS]
    statement = sql.SQL(
        "INSERT INTO {target} ({cols}) SELECT {cols} FROM {staging} "
        "ON CONFLICT ({keys}) DO UPDATE SET {assignments} "
        "WHERE {target}.row_hash IS DISTINCT FROM EXCLUDED.row_hash"
    ).format(
        target=sql.Identifier(table),
        staging=sql.Identifier(_STAGING_TABLE),
        cols=_identifiers(columns),
        keys=_identifiers(_KEY_COLUMNS),
        assignments=sql.SQL(", ").join(_assignment(name) for name in updates),
    )
    cur.execute(statement)
    return cur.rowcount


def _assignment(column: str) -> sql.Composed:
    return sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(column))


def _identifiers(columns: tuple[str, ...] | list[str]) -> sql.Composed:
    return sql.SQL(", ").join(sql.Identifier(name) for name in columns)
