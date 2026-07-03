"""Leitura de abas de dados de planilhas TUSS.

Responsabilidade única: localizar a aba de dados e aplicar o cabeçalho real,
pulando o preâmbulo. Não normaliza colunas nem coage tipos — tudo é lido como
texto para preservar códigos com zero à esquerda.
"""

from pathlib import Path

import fastexcel
import polars as pl

_COVER_SHEET_PREFIXES = ("capa",)
_INDEX_SHEET_NAMES = ("índice", "indice")
_METADATA_SHEET_MARKER = "lista de terminologias"
_HEADER_MARKER_PREFIX = "Código"  # "Código do Termo" no núcleo; "Código" na Tab 63
_HEADER_SCAN_ROWS = 8


def data_sheet_names(xlsx_path: Path) -> list[str]:
    """Nomes das abas de dados de um workbook TUSS, excluindo capa e índice."""
    workbook = fastexcel.read_excel(str(xlsx_path))
    return [name for name in workbook.sheet_names if _is_data_sheet(name)]


def read_tuss_sheet(xlsx_path: Path, sheet_name: str) -> pl.DataFrame:
    """Lê uma aba de dados TUSS: pula o preâmbulo, aplica o cabeçalho real e
    devolve as linhas com os rótulos originais, todas as colunas como texto."""
    raw = _read_sheet_as_text(xlsx_path, sheet_name)
    header_index = _locate_header_row(raw)
    labels = _row_labels(raw, header_index)
    columns = raw.columns[: len(labels)]
    body = raw.slice(header_index + 1).select(columns)
    renamed = body.rename(dict(zip(columns, labels, strict=True)))
    return _drop_blank_rows(renamed, labels[0])


def _is_data_sheet(sheet_name: str) -> bool:
    normalized = sheet_name.strip().lower()
    if normalized.startswith(_COVER_SHEET_PREFIXES):
        return False
    if normalized in _INDEX_SHEET_NAMES:
        return False
    return _METADATA_SHEET_MARKER not in normalized


def _read_sheet_as_text(xlsx_path: Path, sheet_name: str) -> pl.DataFrame:
    return pl.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        has_header=False,
        infer_schema_length=0,
    )


def _locate_header_row(raw: pl.DataFrame) -> int:
    marker_column = raw.get_column(raw.columns[0])
    for index in range(min(_HEADER_SCAN_ROWS, raw.height)):
        value = marker_column[index]
        if value is not None and str(value).startswith(_HEADER_MARKER_PREFIX):
            return index
    raise ValueError(
        f"cabeçalho iniciando por '{_HEADER_MARKER_PREFIX}' não encontrado "
        f"nas primeiras {_HEADER_SCAN_ROWS} linhas"
    )


def _row_labels(raw: pl.DataFrame, row_index: int) -> list[str]:
    labels: list[str] = []
    for value in raw.row(row_index):
        if value is None:
            break
        labels.append(str(value).strip())
    return labels


def _drop_blank_rows(frame: pl.DataFrame, code_column: str) -> pl.DataFrame:
    code = pl.col(code_column)
    return frame.filter(code.is_not_null() & (code.str.strip_chars() != ""))
