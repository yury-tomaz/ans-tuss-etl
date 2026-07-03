from collections.abc import Sequence
from pathlib import Path

import polars as pl
import pytest
import xlsxwriter

from etl_tuss.release_extractor import extract_release

_CORE_HEADER = [
    "Código do Termo",
    "Termo",
    "Data de início de vigência",
    "Data de fim de vigência",
    "Data de fim de implantação",
]
_MED_HEADER = [
    "Código do Termo",
    "Termo",
    "Apresentação",
    "Laboratório",
    "Data de início de vigência",
    "Data de fim de vigência",
    "Data de fim de implantação",
    "REGISTRO ANVISA",
]
_OPME_HEADER = [
    "Código do Termo",
    "Termo",
    "Modelo",
    "Fabricante",
    "Data de início de vigência",
    "Data de fim de vigência",
    "Data de fim de implantação",
    "Registro Anvisa",
    "Classe de Risco",
    "NOME TÉCNICO",
]

type Sheets = Sequence[tuple[str, Sequence[str], Sequence[Sequence[str]]]]


def _write_workbook(path: Path, sheets: Sheets) -> None:
    workbook = xlsxwriter.Workbook(str(path))
    workbook.add_worksheet("Capa")
    for sheet_name, header, rows in sheets:
        sheet = workbook.add_worksheet(sheet_name)
        sheet.write(0, 0, f"Tabela - {sheet_name}")
        for col, label in enumerate(header):
            sheet.write(2, col, label)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                sheet.write_string(3 + r, c, value)
    workbook.close()


def _core_row(codigo: str, termo: str) -> list[str]:
    return [codigo, termo, "2012-10-10", "", ""]


def _med_row(codigo: str) -> list[str]:
    return [codigo, "DIPIRONA", "COMP", "ACME", "2012-10-10", "", "", "123"]


def _opme_row(codigo: str) -> list[str]:
    return [codigo, "STENT", "M1", "ACME", "2012-10-10", "", "", "123", "III", "STENT"]


@pytest.fixture
def release_dir(tmp_path: Path) -> Path:
    root = tmp_path / "release"
    root.mkdir()
    _write_workbook(
        root / "TUSS 18 - DIÁRIAS.xlsx",
        [("Tab 18", _CORE_HEADER, [_core_row("011", "A"), _core_row("012", "B")])],
    )
    _write_workbook(
        root / "TUSS 20 - MEDICAMENTOS.xlsx",
        [("Tab 20", _MED_HEADER, [_med_row("900")])],
    )
    _write_workbook(
        root / "TUSS - Demais terminologias.xlsx",
        [("Tab 23", _CORE_HEADER, [_core_row("1", "Eletivo")])],
    )
    opme = root / "TUSS 19 - OPME"
    opme.mkdir()
    _write_workbook(
        opme / "TUSS 19 - OPME PARTE_1.xlsx",
        [("Materiais parte1", _OPME_HEADER, [_opme_row("019a")])],
    )
    _write_workbook(
        opme / "TUSS 19 - OPME PARTE_2.xlsx",
        [("Materiais parte2", _OPME_HEADER, [_opme_row("019b")])],
    )
    return root


def test_writes_one_core_parquet_per_tabela(release_dir: Path, tmp_path: Path) -> None:
    paths = extract_release(release_dir, tmp_path / "staging", "202601")
    core = sorted(p.name for p in paths if p.name.startswith("tab_"))
    assert core == ["tab_18.parquet", "tab_19.parquet", "tab_20.parquet", "tab_23.parquet"]
    assert all(p.exists() for p in paths)


def test_writes_extension_parquets_for_rich_tabelas(release_dir: Path, tmp_path: Path) -> None:
    paths = extract_release(release_dir, tmp_path / "staging", "202601")
    ext = sorted(p.name for p in paths if p.name.startswith("ext_"))
    assert ext == ["ext_medicamento.parquet", "ext_opme.parquet"]


def test_opme_extension_concatenates_parts(release_dir: Path, tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    extract_release(release_dir, staging, "202601")
    frame = pl.read_parquet(staging / "versao=202601" / "ext_opme.parquet")
    assert frame.height == 2
    assert set(frame["codigo"].to_list()) == {"019a", "019b"}


def test_medicamento_extension_carries_rich_columns(release_dir: Path, tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    extract_release(release_dir, staging, "202601")
    frame = pl.read_parquet(staging / "versao=202601" / "ext_medicamento.parquet")
    assert frame["tabela"].to_list() == ["20"]
    assert frame["laboratorio"].to_list() == ["ACME"]


def test_versao_and_tabela_columns_filled(release_dir: Path, tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    extract_release(release_dir, staging, "202601")
    frame = pl.read_parquet(staging / "versao=202601" / "tab_18.parquet")
    assert frame["versao"].unique().to_list() == ["202601"]
    assert frame["tabela"].unique().to_list() == ["18"]
