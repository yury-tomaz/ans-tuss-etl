from collections.abc import Sequence
from pathlib import Path

import polars as pl
import pytest
import xlsxwriter

from etl_tuss.release_extractor import extract_release

_HEADER = [
    "Código do Termo",
    "Termo",
    "Data de início de vigência",
    "Data de fim de vigência",
    "Data de fim de implantação",
]

type DataSheets = Sequence[tuple[str, Sequence[tuple[str, str]]]]


def _write_workbook(path: Path, data_sheets: DataSheets) -> None:
    workbook = xlsxwriter.Workbook(str(path))
    workbook.add_worksheet("Capa")
    for sheet_name, rows in data_sheets:
        sheet = workbook.add_worksheet(sheet_name)
        sheet.write(0, 0, f"Tabela - {sheet_name}")
        for col, label in enumerate(_HEADER):
            sheet.write(2, col, label)
        for offset, (codigo, termo) in enumerate(rows):
            sheet.write_string(3 + offset, 0, codigo)
            sheet.write(3 + offset, 1, termo)
            sheet.write(3 + offset, 2, "2012-10-10")
    workbook.close()


@pytest.fixture
def release_dir(tmp_path: Path) -> Path:
    root = tmp_path / "release"
    root.mkdir()
    _write_workbook(root / "TUSS 18 - DIÁRIAS.xlsx", [("Tab 18", [("011", "A"), ("012", "B")])])
    _write_workbook(root / "TUSS - Demais terminologias.xlsx", [("Tab 23", [("1", "Eletivo")])])
    opme = root / "TUSS 19 - OPME"
    opme.mkdir()
    _write_workbook(opme / "TUSS 19 - OPME PARTE_1.xlsx", [("Materiais parte1", [("019a", "X")])])
    _write_workbook(opme / "TUSS 19 - OPME PARTE_2.xlsx", [("Materiais parte2", [("019b", "Y")])])
    return root


def test_writes_one_parquet_per_tabela(release_dir: Path, tmp_path: Path) -> None:
    paths = extract_release(release_dir, tmp_path / "staging", "202601")
    assert sorted(p.name for p in paths) == ["tab_18.parquet", "tab_19.parquet", "tab_23.parquet"]
    assert all(p.exists() for p in paths)


def test_opme_parts_are_concatenated(release_dir: Path, tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    extract_release(release_dir, staging, "202601")
    frame = pl.read_parquet(staging / "versao=202601" / "tab_19.parquet")
    assert frame.height == 2
    assert set(frame["codigo"].to_list()) == {"019a", "019b"}


def test_versao_and_tabela_columns_filled(release_dir: Path, tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    extract_release(release_dir, staging, "202601")
    frame = pl.read_parquet(staging / "versao=202601" / "tab_18.parquet")
    assert frame["versao"].unique().to_list() == ["202601"]
    assert frame["tabela"].unique().to_list() == ["18"]
