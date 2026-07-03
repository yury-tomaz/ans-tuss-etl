"""Normalização da extensão de OPME (Tab 19) para o modelo canônico.

Responsabilidade única: mapear os rótulos extras da Tab 19 para campos
canônicos, chaveados por código. Não anexa versão nem hash, nem trata o núcleo
(termo, descrição, datas), que vive na tabela unificada.
"""

from dataclasses import dataclass, fields

import polars as pl


@dataclass(frozen=True)
class OpmeExtensao:
    codigo: str
    modelo: str | None
    fabricante: str | None
    registro_anvisa: str | None
    classe_risco: str | None
    nome_tecnico: str | None


EXTENSION_COLUMNS: tuple[str, ...] = tuple(field.name for field in fields(OpmeExtensao))

_LABEL_TO_CANONICAL = {
    "Código do Termo": "codigo",
    "Modelo": "modelo",
    "Fabricante": "fabricante",
    "Registro Anvisa": "registro_anvisa",
    "Classe de Risco": "classe_risco",
    "NOME TÉCNICO": "nome_tecnico",
}

_KEY_COLUMN = "codigo"
_OPTIONAL_COLUMNS = tuple(name for name in EXTENSION_COLUMNS if name != _KEY_COLUMN)


def normalize_opme(sheet: pl.DataFrame) -> pl.DataFrame:
    """Mapeia as colunas extras da Tab 19 para a extensão canônica de OPME."""
    renamed = sheet.rename(_rename_map(sheet.columns))
    _require_key_column(renamed.columns)
    return renamed.select(
        pl.col(_KEY_COLUMN),
        *(_optional_text(renamed.columns, name) for name in _OPTIONAL_COLUMNS),
    )


def _rename_map(columns: list[str]) -> dict[str, str]:
    return {name: _LABEL_TO_CANONICAL[name] for name in columns if name in _LABEL_TO_CANONICAL}


def _require_key_column(columns: list[str]) -> None:
    if _KEY_COLUMN not in columns:
        raise ValueError(f"coluna chave da extensão ausente: {_KEY_COLUMN!r}")


def _optional_text(columns: list[str], name: str) -> pl.Expr:
    if name in columns:
        return pl.col(name)
    return pl.lit(None, dtype=pl.String).alias(name)
