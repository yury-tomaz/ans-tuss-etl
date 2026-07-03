from datetime import date

import polars as pl
import pytest

from etl_tuss.tuss_schema import CORE_COLUMNS, normalize_core


def _sheet(overrides: dict[str, list[str | None]] | None = None) -> pl.DataFrame:
    base: dict[str, list[str | None]] = {
        "Código do Termo": ["01234567", "00000042"],
        "Termo": ["ALFA", "BETA"],
        "Descrição Detalhada do Termo": ["detalhe", None],
        "Data de início de vigência": ["2012-10-10 00:00:00", "2013-01-01"],
        "Data de fim de vigência": [None, "2020-05-05 00:00:00"],
        "Data de fim de implantação": ["2014-08-31 00:00:00", ""],
    }
    if overrides:
        base.update(overrides)
    return pl.DataFrame(base)


def test_normalize_core_renames_to_canonical() -> None:
    frame = normalize_core(_sheet())
    assert frame.columns == list(CORE_COLUMNS)


def test_normalize_core_parses_dates() -> None:
    frame = normalize_core(_sheet())
    assert frame.schema["inicio_vigencia"] == pl.Date
    assert frame["inicio_vigencia"].to_list() == [date(2012, 10, 10), date(2013, 1, 1)]


def test_normalize_core_preserves_codigo_as_text() -> None:
    frame = normalize_core(_sheet())
    assert frame.schema["codigo"] == pl.String
    assert frame["codigo"].to_list() == ["01234567", "00000042"]


def test_normalize_core_fills_missing_descricao() -> None:
    sheet = _sheet().drop("Descrição Detalhada do Termo")
    frame = normalize_core(sheet)
    assert frame.schema["descricao"] == pl.String
    assert frame["descricao"].to_list() == [None, None]


def test_normalize_core_drops_extra_columns() -> None:
    sheet = _sheet().with_columns(pl.Series("Sigla", ["a", "b"]))
    frame = normalize_core(sheet)
    assert "Sigla" not in frame.columns
    assert frame.columns == list(CORE_COLUMNS)


def test_normalize_core_raises_when_core_column_missing() -> None:
    sheet = _sheet().drop("Termo")
    with pytest.raises(ValueError, match="termo"):
        normalize_core(sheet)


def test_normalize_core_empty_or_null_date_becomes_null() -> None:
    frame = normalize_core(_sheet())
    assert frame["fim_vigencia"].to_list() == [None, date(2020, 5, 5)]
    assert frame["fim_implantacao"].to_list() == [date(2014, 8, 31), None]


def test_normalize_core_accepts_grupo_variant() -> None:
    sheet = pl.DataFrame(
        {
            "Código": ["001"],
            "Grupo": ["ANATOMIA PATOLÓGICA"],
            "Data de início de vigência": ["2012-10-10 00:00:00"],
            "Data de fim de vigência": [None],
            "Data de fim de implantação": [None],
        },
        schema={
            "Código": pl.String,
            "Grupo": pl.String,
            "Data de início de vigência": pl.String,
            "Data de fim de vigência": pl.String,
            "Data de fim de implantação": pl.String,
        },
    )
    frame = normalize_core(sheet)
    assert frame.columns == list(CORE_COLUMNS)
    assert frame["codigo"].to_list() == ["001"]
    assert frame["termo"].to_list() == ["ANATOMIA PATOLÓGICA"]
