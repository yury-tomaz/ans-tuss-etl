"""Orquestração da extração de um release TUSS até o staging.

Descobre as fontes do release, monta cada terminologia (concatenando as partes
do OPME) e grava um Parquet por tabela. Só o núcleo, por ora — as colunas ricas
de medicamentos/OPME ficam para os módulos de extensão.
"""

from pathlib import Path

import polars as pl

from etl_tuss.parquet_writer import write_staging_parquet
from etl_tuss.release_sources import SheetSource, discover_sheet_sources
from etl_tuss.terminology_assembler import assemble_core_terminology


def extract_release(release_dir: Path, staging_root: Path, versao: str) -> list[Path]:
    """Extrai o release inteiro para o staging e devolve os Parquets escritos."""
    grouped = _group_by_tabela(discover_sheet_sources(release_dir))
    return [
        _extract_tabela(tabela, sources, staging_root, versao)
        for tabela, sources in grouped.items()
    ]


def _group_by_tabela(sources: list[SheetSource]) -> dict[str, list[SheetSource]]:
    grouped: dict[str, list[SheetSource]] = {}
    for source in sources:
        grouped.setdefault(source.tabela, []).append(source)
    return grouped


def _extract_tabela(
    tabela: str,
    sources: list[SheetSource],
    staging_root: Path,
    versao: str,
) -> Path:
    frames = [
        assemble_core_terminology(source.xlsx_path, source.sheet_name, versao, tabela)
        for source in sources
    ]
    return write_staging_parquet(pl.concat(frames), staging_root, versao, tabela)
