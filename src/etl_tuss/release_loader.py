"""Carga de um staging inteiro para o PostgreSQL, em ordem segura de FK.

Carrega os Parquets de núcleo (``tab_*.parquet``) em ``tuss_termo`` antes das
extensões ricas, cuja FK exige o termo já presente. Devolve um relatório tipado
com as linhas afetadas por tabela de destino.
"""

from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from etl_tuss.postgres_loader import load_parquet

_MEDICAMENTO_PARQUET = "ext_medicamento.parquet"
_OPME_PARQUET = "ext_opme.parquet"


@dataclass(frozen=True)
class LoadReport:
    termo: int
    medicamento: int
    opme: int


def load_release(
    conn: psycopg.Connection[TupleRow],
    staging_root: Path,
    versao: str,
) -> LoadReport:
    """Carrega o staging da versão (núcleo e depois extensões) e relata as linhas afetadas."""
    version_dir = staging_root / f"versao={versao}"
    return LoadReport(
        termo=_load_core(conn, version_dir),
        medicamento=_load_extension(conn, version_dir, _MEDICAMENTO_PARQUET, "tuss_medicamento"),
        opme=_load_extension(conn, version_dir, _OPME_PARQUET, "tuss_opme"),
    )


def _load_core(conn: psycopg.Connection[TupleRow], version_dir: Path) -> int:
    return sum(
        load_parquet(conn, path, "tuss_termo") for path in sorted(version_dir.glob("tab_*.parquet"))
    )


def _load_extension(
    conn: psycopg.Connection[TupleRow],
    version_dir: Path,
    filename: str,
    table: str,
) -> int:
    path = version_dir / filename
    if not path.exists():
        return 0
    return load_parquet(conn, path, table)
