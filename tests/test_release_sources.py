from collections.abc import Sequence
from pathlib import Path

import pytest
import xlsxwriter

from etl_tuss.release_sources import discover_sheet_sources


def _write_xlsx(path: Path, sheet_names: Sequence[str]) -> None:
    workbook = xlsxwriter.Workbook(str(path))
    for name in sheet_names:
        workbook.add_worksheet(name)
    workbook.close()


@pytest.fixture
def release_dir(tmp_path: Path) -> Path:
    _write_xlsx(tmp_path / "TUSS 18 - DIÁRIAS E TAXAS - VERSÃO 202601.xlsx", ["Capa", "Tab 18"])
    _write_xlsx(
        tmp_path / "TUSS - Demais terminologias - VERSÃO 202601.xlsx",
        ["Capa", "Índice", "Tab 23", "Tab 24", "Lista de terminologias"],
    )
    opme = tmp_path / "TUSS 19 - materiais e OPME"
    opme.mkdir()
    _write_xlsx(opme / "TUSS 19 - materiais e OPME - VERSÃO 202601_PARTE_1.xlsx", ["Capa", "P1"])
    _write_xlsx(opme / "TUSS 19 - materiais e OPME - VERSÃO 202601_PARTE_2.xlsx", ["Capa", "P2"])
    _write_xlsx(tmp_path / "~$lock.xlsx", ["Capa", "Tab 99"])
    _write_xlsx(tmp_path / "TUSS 64 - Envio de dados para ANS.xlsx", ["Capa", "Tab 18"])
    return tmp_path


def test_standalone_file_maps_to_tabela(release_dir: Path) -> None:
    sources = discover_sheet_sources(release_dir)
    tab_18 = [s for s in sources if s.tabela == "18"]
    assert len(tab_18) == 1
    assert tab_18[0].sheet_name == "Tab 18"


def test_demais_workbook_excludes_cover_index_and_list(release_dir: Path) -> None:
    tabelas = {s.tabela for s in discover_sheet_sources(release_dir)}
    assert {"23", "24"} <= tabelas


def test_opme_yields_two_parts(release_dir: Path) -> None:
    tab_19 = [s for s in discover_sheet_sources(release_dir) if s.tabela == "19"]
    assert len(tab_19) == 2


def test_lock_and_submission_are_ignored(release_dir: Path) -> None:
    tabelas = [s.tabela for s in discover_sheet_sources(release_dir)]
    assert tabelas == ["18", "19", "19", "23", "24"]


def test_unknown_xlsx_raises(tmp_path: Path) -> None:
    _write_xlsx(tmp_path / "planilha aleatoria.xlsx", ["Capa", "Dados"])
    with pytest.raises(ValueError, match="não reconhecido"):
        discover_sheet_sources(tmp_path)
