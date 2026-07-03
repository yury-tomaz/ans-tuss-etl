import polars as pl
import pytest

from etl_tuss.opme_schema import EXTENSION_COLUMNS, normalize_opme


def _sheet(overrides: dict[str, list[str | None]] | None = None) -> pl.DataFrame:
    base: dict[str, list[str | None]] = {
        "Código do Termo": ["80000001", "80000002"],
        "Termo": ["STENT", "PRÓTESE"],
        "Modelo": ["M1", None],
        "Fabricante": ["ACME", "BETA MED"],
        "Data de início de vigência": ["2012-10-10", "2013-01-01"],
        "Registro Anvisa": ["1234567890", None],
        "Classe de Risco": ["III", "IV"],
        "NOME TÉCNICO": ["STENT CORONÁRIO", None],
    }
    if overrides:
        base.update(overrides)
    return pl.DataFrame(base)


def test_normalize_opme_keeps_only_extension_columns() -> None:
    frame = normalize_opme(_sheet())
    assert frame.columns == list(EXTENSION_COLUMNS)


def test_normalize_opme_preserves_codigo_as_text() -> None:
    frame = normalize_opme(_sheet())
    assert frame.schema["codigo"] == pl.String
    assert frame["codigo"].to_list() == ["80000001", "80000002"]


def test_normalize_opme_maps_extra_columns() -> None:
    frame = normalize_opme(_sheet())
    assert frame["modelo"].to_list() == ["M1", None]
    assert frame["fabricante"].to_list() == ["ACME", "BETA MED"]
    assert frame["registro_anvisa"].to_list() == ["1234567890", None]
    assert frame["classe_risco"].to_list() == ["III", "IV"]
    assert frame["nome_tecnico"].to_list() == ["STENT CORONÁRIO", None]


def test_normalize_opme_fills_missing_optional() -> None:
    sheet = _sheet().drop("Classe de Risco")
    frame = normalize_opme(sheet)
    assert frame["classe_risco"].to_list() == [None, None]


def test_normalize_opme_raises_without_codigo() -> None:
    sheet = _sheet().drop("Código do Termo")
    with pytest.raises(ValueError, match="codigo"):
        normalize_opme(sheet)
