"""Descoberta das fontes de terminologia num release TUSS.

Varre o diretório de um release e mapeia, por convenção de nome, cada (arquivo,
aba de dados) para o número da tabela. Não lê o conteúdo das abas — só resolve o
que deve ser extraído. Nada casa por regra é ignorado silenciosamente: um .xlsx
desconhecido levanta ValueError.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from etl_tuss.sheet_reader import data_sheet_names

_LOCK_PREFIX = "~$"
_SUBMISSION_MARKER = "TUSS 64"  # formato de envio à ANS; duplica tabelas primárias
_MULTI_WORKBOOK_MARKER = "Demais terminologias"
_FILENAME_TABELA = re.compile(r"TUSS (\d+)")
_SHEET_TABELA = re.compile(r"Tab (\d+)")


@dataclass(frozen=True)
class SheetSource:
    tabela: str
    xlsx_path: Path
    sheet_name: str


def discover_sheet_sources(release_dir: Path) -> list[SheetSource]:
    """Uma fonte por (arquivo, aba de dados) do release, ordenada por tabela."""
    if not release_dir.is_dir():
        raise ValueError(f"diretório do release não encontrado: {release_dir}")
    sources: list[SheetSource] = []
    for xlsx_path in sorted(release_dir.rglob("*.xlsx")):
        if _is_ignored(xlsx_path.name):
            continue
        sources.extend(_sources_from_file(xlsx_path))
    if not sources:
        raise ValueError(f"nenhuma planilha de terminologia encontrada em {release_dir}")
    return sorted(sources, key=_sort_key)


def _is_ignored(name: str) -> bool:
    return name.startswith(_LOCK_PREFIX) or _SUBMISSION_MARKER in name


def _sources_from_file(xlsx_path: Path) -> list[SheetSource]:
    if _MULTI_WORKBOOK_MARKER in xlsx_path.name:
        return _multi_workbook_sources(xlsx_path)
    return [_standalone_source(xlsx_path)]


def _multi_workbook_sources(xlsx_path: Path) -> list[SheetSource]:
    return [
        SheetSource(_tabela_from_sheet(sheet_name), xlsx_path, sheet_name)
        for sheet_name in data_sheet_names(xlsx_path)
    ]


def _standalone_source(xlsx_path: Path) -> SheetSource:
    sheets = data_sheet_names(xlsx_path)
    if len(sheets) != 1:
        raise ValueError(f"esperava uma aba de dados em {xlsx_path.name!r}, achei {sheets}")
    return SheetSource(_tabela_from_filename(xlsx_path.name), xlsx_path, sheets[0])


def _tabela_from_filename(name: str) -> str:
    match = _FILENAME_TABELA.search(name)
    if match is None:
        raise ValueError(f"arquivo .xlsx não reconhecido: {name!r}")
    return match.group(1)


def _tabela_from_sheet(sheet_name: str) -> str:
    match = _SHEET_TABELA.search(sheet_name)
    if match is None:
        raise ValueError(f"aba sem número de tabela: {sheet_name!r}")
    return match.group(1)


def _sort_key(source: SheetSource) -> tuple[int, str]:
    return (int(source.tabela), source.sheet_name)
