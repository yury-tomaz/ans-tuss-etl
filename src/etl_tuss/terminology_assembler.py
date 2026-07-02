"""Montagem de uma terminologia TUSS pronta para o staging.

Junta leitura, normalização do núcleo e fingerprint: uma aba de um release vira
um frame com ``versao``, ``tabela`` e ``row_hash`` anexados. Puro e por
terminologia — iterar abas ou concatenar partes é responsabilidade de quem
orquestra o release.
"""

from pathlib import Path

import polars as pl

from etl_tuss.content_hash import content_hash
from etl_tuss.sheet_reader import read_tuss_sheet
from etl_tuss.tuss_schema import normalize_core

_CONTENT_COLUMNS = ("termo", "descricao", "inicio_vigencia", "fim_vigencia", "fim_implantacao")
_OUTPUT_COLUMNS = ("versao", "tabela", "codigo", *_CONTENT_COLUMNS, "row_hash")


def assemble_core_terminology(
    xlsx_path: Path,
    sheet_name: str,
    versao: str,
    tabela: str,
) -> pl.DataFrame:
    """Lê e normaliza uma aba e anexa ``versao``, ``tabela`` e ``row_hash``."""
    core = normalize_core(read_tuss_sheet(xlsx_path, sheet_name))
    with_hash = core.with_columns(
        pl.lit(versao).alias("versao"),
        pl.lit(tabela).alias("tabela"),
        content_hash(core, _CONTENT_COLUMNS),
    )
    return with_hash.select(_OUTPUT_COLUMNS)
