import polars as pl
import pytest

from etl_tuss.medicamento_schema import EXTENSION_COLUMNS, normalize_medicamento


def _sheet(overrides: dict[str, list[str | None]] | None = None) -> pl.DataFrame:
    base: dict[str, list[str | None]] = {
        "Código do Termo": ["90000001", "90000002"],
        "Termo": ["DIPIRONA", "PARACETAMOL"],
        "Apresentação": ["COMP 50MG", None],
        "Laboratório": ["ACME", "BETA PHARMA"],
        "Data de início de vigência": ["2012-10-10", "2013-01-01"],
        "REGISTRO ANVISA": ["1234567890", None],
    }
    if overrides:
        base.update(overrides)
    return pl.DataFrame(base)


def test_normalize_medicamento_keeps_only_extension_columns() -> None:
    frame = normalize_medicamento(_sheet())
    assert frame.columns == list(EXTENSION_COLUMNS)


def test_normalize_medicamento_preserves_codigo_as_text() -> None:
    frame = normalize_medicamento(_sheet())
    assert frame.schema["codigo"] == pl.String
    assert frame["codigo"].to_list() == ["90000001", "90000002"]


def test_normalize_medicamento_maps_extra_columns() -> None:
    frame = normalize_medicamento(_sheet())
    assert frame["apresentacao"].to_list() == ["COMP 50MG", None]
    assert frame["laboratorio"].to_list() == ["ACME", "BETA PHARMA"]
    assert frame["registro_anvisa"].to_list() == ["1234567890", None]


def test_normalize_medicamento_fills_missing_optional() -> None:
    sheet = _sheet().drop("Laboratório")
    frame = normalize_medicamento(sheet)
    assert frame["laboratorio"].to_list() == [None, None]


def test_normalize_medicamento_raises_without_codigo() -> None:
    sheet = _sheet().drop("Código do Termo")
    with pytest.raises(ValueError, match="codigo"):
        normalize_medicamento(sheet)
