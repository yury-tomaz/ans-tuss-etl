"""Escrita do staging em Parquet, no layout particionado por versão (ADR 0005).

Grava um frame de terminologia em ``staging_root/versao=<v>/tab_<NN>.parquet``.
A escrita é atômica (arquivo temporário + rename) para nunca deixar um Parquet
truncado se o processo morrer no meio.
"""

import os
import tempfile
from pathlib import Path

import polars as pl


def write_staging_parquet(
    frame: pl.DataFrame,
    staging_root: Path,
    versao: str,
    tabela: str,
) -> Path:
    """Grava o frame no caminho de staging da versão/tabela e devolve o caminho."""
    target = _staging_path(staging_root, versao, tabela)
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(frame, target)
    return target


def _staging_path(staging_root: Path, versao: str, tabela: str) -> Path:
    return staging_root / f"versao={versao}" / f"tab_{tabela}.parquet"


def _write_atomic(frame: pl.DataFrame, target: Path) -> None:
    descriptor, temp_name = tempfile.mkstemp(dir=target.parent, suffix=".parquet.tmp")
    os.close(descriptor)
    temp_path = Path(temp_name)
    try:
        frame.write_parquet(temp_path)
        os.replace(temp_path, target)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
