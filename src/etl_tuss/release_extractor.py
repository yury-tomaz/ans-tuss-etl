"""Orquestração da extração de um release TUSS até o staging.

Descobre as fontes do release, monta cada terminologia do núcleo (concatenando
as partes do OPME) e grava um Parquet por tabela. Para as terminologias ricas
(medicamentos Tab 20, OPME Tab 19) grava também um Parquet de extensão ao lado
do núcleo.
"""

from collections.abc import Callable
from pathlib import Path

import polars as pl

from etl_tuss.extension_assembler import (
    assemble_medicamento_extension,
    assemble_opme_extension,
)
from etl_tuss.parquet_writer import write_extension_parquet, write_staging_parquet
from etl_tuss.release_sources import SheetSource, discover_sheet_sources
from etl_tuss.terminology_assembler import assemble_core_terminology

type _ExtensionAssembler = Callable[[Path, str, str], pl.DataFrame]

_EXTENSION_ASSEMBLERS: dict[str, tuple[_ExtensionAssembler, str]] = {
    "20": (assemble_medicamento_extension, "medicamento"),
    "19": (assemble_opme_extension, "opme"),
}


def extract_release(release_dir: Path, staging_root: Path, versao: str) -> list[Path]:
    """Extrai o release inteiro para o staging e devolve os Parquets escritos."""
    grouped = _group_by_tabela(discover_sheet_sources(release_dir))
    return [
        path
        for tabela, sources in grouped.items()
        for path in _extract_tabela(tabela, sources, staging_root, versao)
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
) -> list[Path]:
    core = pl.concat(
        assemble_core_terminology(source.xlsx_path, source.sheet_name, versao, tabela)
        for source in sources
    )
    core_path = write_staging_parquet(core, staging_root, versao, tabela)
    return [core_path, *_extract_extension(tabela, sources, staging_root, versao)]


def _extract_extension(
    tabela: str,
    sources: list[SheetSource],
    staging_root: Path,
    versao: str,
) -> list[Path]:
    dispatch = _EXTENSION_ASSEMBLERS.get(tabela)
    if dispatch is None:
        return []
    assemble, nome = dispatch
    frame = pl.concat(assemble(source.xlsx_path, source.sheet_name, versao) for source in sources)
    return [write_extension_parquet(frame, staging_root, versao, nome)]
