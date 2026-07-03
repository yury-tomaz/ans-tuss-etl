from pathlib import Path

import pytest
import xlsxwriter

from etl_tuss.sheet_reader import data_sheet_names, read_tuss_sheet

_HEADER = ["Código do Termo", "Termo", "Data de início de vigência"]


@pytest.fixture
def tuss_xlsx(tmp_path: Path) -> Path:
    """Planilha sintética no layout TUSS: aba de capa + aba de dados com
    título, linha em branco, cabeçalho na sequência e códigos com zero à
    esquerda."""
    path = tmp_path / "tuss_sample.xlsx"
    workbook = xlsxwriter.Workbook(str(path))
    workbook.add_worksheet("Capa")
    sheet = workbook.add_worksheet("Tab 99")
    sheet.write(0, 0, "Tabela 99 - Terminologia de teste")
    for col, label in enumerate(_HEADER):
        sheet.write(2, col, label)
    sheet.write_string(3, 0, "01234567")
    sheet.write(3, 1, "ALFA")
    sheet.write(3, 2, "2012-10-10")
    sheet.write_string(4, 0, "00000042")
    sheet.write(4, 1, "BETA")
    sheet.write(4, 2, "2013-01-01")
    workbook.close()
    return path


def test_data_sheet_names_excludes_cover(tuss_xlsx: Path) -> None:
    assert data_sheet_names(tuss_xlsx) == ["Tab 99"]


def test_read_tuss_sheet_applies_real_header(tuss_xlsx: Path) -> None:
    frame = read_tuss_sheet(tuss_xlsx, "Tab 99")
    assert frame.columns == _HEADER


def test_read_tuss_sheet_preserves_leading_zero_codes(tuss_xlsx: Path) -> None:
    frame = read_tuss_sheet(tuss_xlsx, "Tab 99")
    assert frame["Código do Termo"].to_list() == ["01234567", "00000042"]


def test_read_tuss_sheet_skips_preamble(tuss_xlsx: Path) -> None:
    frame = read_tuss_sheet(tuss_xlsx, "Tab 99")
    assert frame.height == 2
    assert frame["Termo"].to_list() == ["ALFA", "BETA"]


@pytest.fixture
def tuss_grupo_xlsx(tmp_path: Path) -> Path:
    """Variante Tab 63: rótulos 'Código'/'Grupo' e cabeçalho logo após o
    título, sem linha em branco de preâmbulo."""
    path = tmp_path / "tuss_grupo.xlsx"
    workbook = xlsxwriter.Workbook(str(path))
    workbook.add_worksheet("Capa")
    sheet = workbook.add_worksheet("Tab 63")
    sheet.write(0, 0, "Tabela 63 - Grupos de procedimentos")
    for col, label in enumerate(("Código", "Grupo", "Data de início de vigência")):
        sheet.write(1, col, label)
    sheet.write_string(2, 0, "001")
    sheet.write(2, 1, "ANATOMIA PATOLÓGICA")
    sheet.write(2, 2, "2012-10-10")
    workbook.close()
    return path


def test_read_tuss_sheet_handles_grupo_variant(tuss_grupo_xlsx: Path) -> None:
    frame = read_tuss_sheet(tuss_grupo_xlsx, "Tab 63")
    assert frame.columns == ["Código", "Grupo", "Data de início de vigência"]
    assert frame["Código"].to_list() == ["001"]
    assert frame["Grupo"].to_list() == ["ANATOMIA PATOLÓGICA"]
