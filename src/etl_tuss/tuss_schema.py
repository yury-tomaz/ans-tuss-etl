"""Normalização de uma aba TUSS lida como texto para o núcleo canônico.

Responsabilidade única: renomear os rótulos da ANS para os campos canônicos,
parsear as datas e descartar colunas fora do núcleo. Não anexa versão, tabela
ou hash, nem trata colunas de terminologias ricas.
"""

from dataclasses import dataclass, fields
from datetime import date

import polars as pl


@dataclass(frozen=True)
class TussTermo:
    codigo: str
    termo: str
    descricao: str | None
    inicio_vigencia: date | None
    fim_vigencia: date | None
    fim_implantacao: date | None


CORE_COLUMNS: tuple[str, ...] = tuple(field.name for field in fields(TussTermo))

_LABEL_TO_CANONICAL = {
    "Código do Termo": "codigo",
    "Termo": "termo",
    "Descrição Detalhada do Termo": "descricao",
    "Descrição Detalhada": "descricao",
    "Descrição detalhada": "descricao",
    "Data de início de vigência": "inicio_vigencia",
    "Data de fim de vigência": "fim_vigencia",
    "Data de fim de implantação": "fim_implantacao",
}

_OPTIONAL_COLUMN = "descricao"
_REQUIRED_COLUMNS = tuple(name for name in CORE_COLUMNS if name != _OPTIONAL_COLUMN)
_DATE_COLUMNS = ("inicio_vigencia", "fim_vigencia", "fim_implantacao")


def normalize_core(sheet: pl.DataFrame) -> pl.DataFrame:
    """Mapeia as colunas de uma aba TUSS (texto) para o núcleo canônico tipado."""
    renamed = sheet.rename(_rename_map(sheet.columns))
    _require_core_columns(renamed.columns)
    return renamed.select(
        pl.col("codigo"),
        pl.col("termo"),
        _optional_text(renamed.columns, _OPTIONAL_COLUMN),
        *(_parse_date(name) for name in _DATE_COLUMNS),
    )


def _rename_map(columns: list[str]) -> dict[str, str]:
    return {name: _LABEL_TO_CANONICAL[name] for name in columns if name in _LABEL_TO_CANONICAL}


def _require_core_columns(columns: list[str]) -> None:
    missing = [name for name in _REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise ValueError(f"colunas obrigatórias do núcleo ausentes: {missing}")


def _optional_text(columns: list[str], name: str) -> pl.Expr:
    if name in columns:
        return pl.col(name)
    return pl.lit(None, dtype=pl.String).alias(name)


def _parse_date(name: str) -> pl.Expr:
    return pl.col(name).str.slice(0, 10).str.to_date("%Y-%m-%d", strict=False).alias(name)
