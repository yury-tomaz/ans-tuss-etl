"""Montagem das extensões ricas (medicamentos, OPME) prontas para o staging.

Cada extensão vira um frame chaveado por código com ``versao``, ``tabela`` e
``row_hash`` anexados. O núcleo (termo, descrição, datas) não é repetido — vive
na tabela unificada e se junta por código (ADR 0006).
"""

from collections.abc import Sequence
from pathlib import Path

import polars as pl

from etl_tuss.content_hash import content_hash
from etl_tuss.medicamento_schema import EXTENSION_COLUMNS as MEDICAMENTO_COLUMNS
from etl_tuss.medicamento_schema import normalize_medicamento
from etl_tuss.opme_schema import EXTENSION_COLUMNS as OPME_COLUMNS
from etl_tuss.opme_schema import normalize_opme
from etl_tuss.sheet_reader import read_tuss_sheet

_MEDICAMENTO_TABELA = "20"
_OPME_TABELA = "19"
_KEY_COLUMN = "codigo"


def assemble_medicamento_extension(xlsx_path: Path, sheet_name: str, versao: str) -> pl.DataFrame:
    """Monta a extensão de medicamentos (Tab 20) para o staging."""
    extension = normalize_medicamento(read_tuss_sheet(xlsx_path, sheet_name))
    return _finalize(extension, versao, _MEDICAMENTO_TABELA, MEDICAMENTO_COLUMNS)


def assemble_opme_extension(xlsx_path: Path, sheet_name: str, versao: str) -> pl.DataFrame:
    """Monta a extensão de OPME (Tab 19) para o staging."""
    extension = normalize_opme(read_tuss_sheet(xlsx_path, sheet_name))
    return _finalize(extension, versao, _OPME_TABELA, OPME_COLUMNS)


def _finalize(
    extension: pl.DataFrame,
    versao: str,
    tabela: str,
    extension_columns: Sequence[str],
) -> pl.DataFrame:
    content_columns = tuple(name for name in extension_columns if name != _KEY_COLUMN)
    with_hash = extension.with_columns(
        pl.lit(versao).alias("versao"),
        pl.lit(tabela).alias("tabela"),
        content_hash(extension, content_columns),
    )
    return with_hash.select("versao", "tabela", _KEY_COLUMN, *content_columns, "row_hash")
