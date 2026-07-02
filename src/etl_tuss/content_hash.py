"""Fingerprint determinístico do conteúdo de linhas TUSS.

Usado para upsert idempotente e diff entre releases (ADR 0003). O hash é
SHA-256 (estável entre versões do Polars, ao contrário de ``Series.hash``) sobre
uma string canônica das colunas de conteúdo.
"""

import hashlib
from collections.abc import Sequence

import polars as pl

_FIELD_SEPARATOR = "\x1f"
_NULL_SENTINEL = "__NULL__"
_HASH_COLUMN = "row_hash"


def content_hash(frame: pl.DataFrame, columns: Sequence[str]) -> pl.Series:
    """SHA-256 hex determinístico do conteúdo de ``columns``, na ordem dada."""
    fields = [_normalized_field(frame.schema[name], name) for name in columns]
    canonical = frame.select(pl.concat_str(fields, separator=_FIELD_SEPARATOR)).to_series()
    return canonical.map_elements(_sha256_hex, return_dtype=pl.String).rename(_HASH_COLUMN)


def _normalized_field(dtype: pl.DataType, name: str) -> pl.Expr:
    column = pl.col(name)
    as_text = column.str.strip_chars() if dtype == pl.String else column.cast(pl.String)
    return as_text.fill_null(_NULL_SENTINEL)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
