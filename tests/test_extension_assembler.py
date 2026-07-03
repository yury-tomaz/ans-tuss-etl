from collections.abc import Sequence
from pathlib import Path

import xlsxwriter

from etl_tuss.extension_assembler import (
    assemble_medicamento_extension,
    assemble_opme_extension,
)

_MED_HEADER = [
    "Código do Termo",
    "Termo",
    "Apresentação",
    "Laboratório",
    "Data de início de vigência",
    "REGISTRO ANVISA",
]
_OPME_HEADER = [
    "Código do Termo",
    "Termo",
    "Modelo",
    "Fabricante",
    "Data de início de vigência",
    "Registro Anvisa",
    "Classe de Risco",
    "NOME TÉCNICO",
]


def _write_sheet(
    path: Path,
    sheet_name: str,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> None:
    workbook = xlsxwriter.Workbook(str(path))
    workbook.add_worksheet("Capa")
    sheet = workbook.add_worksheet(sheet_name)
    sheet.write(0, 0, f"Tabela - {sheet_name}")
    for col, label in enumerate(header):
        sheet.write(2, col, label)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            sheet.write_string(3 + r, c, value)
    workbook.close()


def test_medicamento_extension_has_expected_columns(tmp_path: Path) -> None:
    path = tmp_path / "med.xlsx"
    _write_sheet(
        path,
        "Tab 20",
        _MED_HEADER,
        [["90000001", "DIPIRONA", "COMP 50MG", "ACME", "2012-10-10", "123"]],
    )
    frame = assemble_medicamento_extension(path, "Tab 20", "202601")
    assert frame.columns == [
        "versao",
        "tabela",
        "codigo",
        "apresentacao",
        "laboratorio",
        "registro_anvisa",
        "row_hash",
    ]
    assert frame["tabela"].to_list() == ["20"]
    assert frame["codigo"].to_list() == ["90000001"]


def test_opme_extension_has_expected_columns(tmp_path: Path) -> None:
    path = tmp_path / "opme.xlsx"
    _write_sheet(
        path,
        "Tab 19",
        _OPME_HEADER,
        [["80000001", "STENT", "M1", "ACME", "2012-10-10", "123", "III", "STENT CORONÁRIO"]],
    )
    frame = assemble_opme_extension(path, "Tab 19", "202601")
    assert frame.columns == [
        "versao",
        "tabela",
        "codigo",
        "modelo",
        "fabricante",
        "registro_anvisa",
        "classe_risco",
        "nome_tecnico",
        "row_hash",
    ]
    assert frame["tabela"].to_list() == ["19"]


def test_medicamento_extension_fills_row_hash(tmp_path: Path) -> None:
    path = tmp_path / "med.xlsx"
    _write_sheet(
        path,
        "Tab 20",
        _MED_HEADER,
        [["90000001", "DIPIRONA", "COMP 50MG", "ACME", "2012-10-10", "123"]],
    )
    frame = assemble_medicamento_extension(path, "Tab 20", "202601")
    assert frame["row_hash"].to_list()[0]
