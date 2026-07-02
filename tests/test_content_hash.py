from collections.abc import Sequence
from datetime import date

import polars as pl

from etl_tuss.content_hash import content_hash

_COLUMNS = ["termo", "descricao", "inicio_vigencia", "fim_vigencia", "fim_implantacao"]

# Trava o formato canônico: string
# "Consulta em consultório\x1f__NULL__\x1f2009-02-13\x1f__NULL__\x1f2010-10-15".
_GOLDEN = "b8c51b8a065d7b0564665a907d2ece4f61835c6b66c0453ac3b23ca1d4d53be1"


def _frame(**overrides: Sequence[str | date | None]) -> pl.DataFrame:
    base: dict[str, Sequence[str | date | None]] = {
        "termo": ["Consulta em consultório"],
        "descricao": [None],
        "inicio_vigencia": [date(2009, 2, 13)],
        "fim_vigencia": [None],
        "fim_implantacao": [date(2010, 10, 15)],
    }
    base.update(overrides)
    return pl.DataFrame(base)


def test_content_hash_is_named_row_hash() -> None:
    assert content_hash(_frame(), _COLUMNS).name == "row_hash"


def test_content_hash_matches_golden_vector() -> None:
    assert content_hash(_frame(), _COLUMNS).to_list() == [_GOLDEN]


def test_identical_content_hashes_equal() -> None:
    assert content_hash(_frame(), _COLUMNS).to_list() == content_hash(_frame(), _COLUMNS).to_list()


def test_null_differs_from_empty_string() -> None:
    with_null = content_hash(_frame(descricao=[None]), _COLUMNS).to_list()
    with_empty = content_hash(_frame(descricao=[""]), _COLUMNS).to_list()
    assert with_null != with_empty


def test_edge_whitespace_is_ignored() -> None:
    trimmed = content_hash(_frame(termo=["Consulta em consultório"]), _COLUMNS).to_list()
    padded = content_hash(_frame(termo=["  Consulta em consultório  "]), _COLUMNS).to_list()
    assert trimmed == padded


def test_change_in_any_column_changes_hash() -> None:
    base = content_hash(_frame(), _COLUMNS).to_list()
    changed = content_hash(_frame(fim_vigencia=[date(2021, 1, 1)]), _COLUMNS).to_list()
    assert base != changed


def test_different_content_differs() -> None:
    a = content_hash(_frame(termo=["ALFA"]), _COLUMNS).to_list()
    b = content_hash(_frame(termo=["BETA"]), _COLUMNS).to_list()
    assert a != b
