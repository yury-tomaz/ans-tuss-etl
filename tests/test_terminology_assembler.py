from pathlib import Path

import pytest
import xlsxwriter

from etl_tuss.content_hash import content_hash
from etl_tuss.terminology_assembler import assemble_core_terminology

_HEADER = [
    "Código do Termo",
    "Termo",
    "Data de início de vigência",
    "Data de fim de vigência",
    "Data de fim de implantação",
]
_CONTENT_COLUMNS = ["termo", "descricao", "inicio_vigencia", "fim_vigencia", "fim_implantacao"]
_EXPECTED_COLUMNS = ["versao", "tabela", "codigo", *_CONTENT_COLUMNS, "row_hash"]


@pytest.fixture
def tuss_xlsx(tmp_path: Path) -> Path:
    path = tmp_path / "tab.xlsx"
    workbook = xlsxwriter.Workbook(str(path))
    workbook.add_worksheet("Capa")
    sheet = workbook.add_worksheet("Tab 23")
    sheet.write(0, 0, "Tabela 23 - Terminologia de teste")
    for col, label in enumerate(_HEADER):
        sheet.write(2, col, label)
    sheet.write_string(3, 0, "01")
    sheet.write(3, 1, "Eletivo")
    sheet.write(3, 2, "2012-10-10")
    sheet.write(3, 4, "2014-08-31")
    sheet.write_string(4, 0, "02")
    sheet.write(4, 1, "Urgência")
    sheet.write(4, 2, "2012-10-10")
    sheet.write(4, 4, "2014-08-31")
    workbook.close()
    return path


def test_output_columns_in_order(tuss_xlsx: Path) -> None:
    frame = assemble_core_terminology(tuss_xlsx, "Tab 23", "202601", "23")
    assert frame.columns == _EXPECTED_COLUMNS


def test_versao_and_tabela_are_filled(tuss_xlsx: Path) -> None:
    frame = assemble_core_terminology(tuss_xlsx, "Tab 23", "202601", "23")
    assert frame["versao"].to_list() == ["202601", "202601"]
    assert frame["tabela"].to_list() == ["23", "23"]


def test_codigo_kept_as_text(tuss_xlsx: Path) -> None:
    frame = assemble_core_terminology(tuss_xlsx, "Tab 23", "202601", "23")
    assert frame["codigo"].to_list() == ["01", "02"]


def test_row_hash_matches_content(tuss_xlsx: Path) -> None:
    frame = assemble_core_terminology(tuss_xlsx, "Tab 23", "202601", "23")
    assert frame["row_hash"].to_list() == content_hash(frame, _CONTENT_COLUMNS).to_list()


def test_row_hash_independent_of_versao(tuss_xlsx: Path) -> None:
    first = assemble_core_terminology(tuss_xlsx, "Tab 23", "202601", "23")
    later = assemble_core_terminology(tuss_xlsx, "Tab 23", "202512", "23")
    assert first["row_hash"].to_list() == later["row_hash"].to_list()
