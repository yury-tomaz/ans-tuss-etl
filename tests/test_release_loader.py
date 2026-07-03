from datetime import date
from pathlib import Path

import polars as pl
import psycopg
from psycopg.rows import TupleRow

from etl_tuss.release_loader import LoadReport, load_release

_CORE_SCHEMA = {
    "versao": pl.String,
    "tabela": pl.String,
    "codigo": pl.String,
    "termo": pl.String,
    "descricao": pl.String,
    "inicio_vigencia": pl.Date,
    "fim_vigencia": pl.Date,
    "fim_implantacao": pl.Date,
    "row_hash": pl.String,
}


def _core(tabela: str, codigo: str, termo: str) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "versao": ["202601"],
            "tabela": [tabela],
            "codigo": [codigo],
            "termo": [termo],
            "descricao": [None],
            "inicio_vigencia": [date(2012, 10, 10)],
            "fim_vigencia": [None],
            "fim_implantacao": [None],
            "row_hash": [f"h-{tabela}-{codigo}"],
        },
        schema=_CORE_SCHEMA,
    )


def _medicamento() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "versao": ["202601"],
            "tabela": ["20"],
            "codigo": ["900"],
            "apresentacao": ["COMP 50MG"],
            "laboratorio": ["ACME"],
            "registro_anvisa": ["123"],
            "row_hash": ["m-900"],
        }
    )


def _opme() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "versao": ["202601"],
            "tabela": ["19"],
            "codigo": ["019a"],
            "modelo": ["M1"],
            "fabricante": ["ACME"],
            "registro_anvisa": ["123"],
            "classe_risco": ["III"],
            "nome_tecnico": ["STENT"],
            "row_hash": ["o-019a"],
        }
    )


def _write_staging(root: Path, *, with_extensions: bool) -> Path:
    version_dir = root / "versao=202601"
    version_dir.mkdir(parents=True)
    _core("18", "011", "A").write_parquet(version_dir / "tab_18.parquet")
    _core("19", "019a", "STENT").write_parquet(version_dir / "tab_19.parquet")
    _core("20", "900", "DIPIRONA").write_parquet(version_dir / "tab_20.parquet")
    if with_extensions:
        _medicamento().write_parquet(version_dir / "ext_medicamento.parquet")
        _opme().write_parquet(version_dir / "ext_opme.parquet")
    return root


def test_load_release_loads_core_then_extensions(
    conn: psycopg.Connection[TupleRow], tmp_path: Path
) -> None:
    staging = _write_staging(tmp_path / "staging", with_extensions=True)
    report = load_release(conn, staging, "202601")
    assert report == LoadReport(termo=3, medicamento=1, opme=1)


def test_load_release_is_idempotent(conn: psycopg.Connection[TupleRow], tmp_path: Path) -> None:
    staging = _write_staging(tmp_path / "staging", with_extensions=True)
    load_release(conn, staging, "202601")
    report = load_release(conn, staging, "202601")
    assert report == LoadReport(termo=0, medicamento=0, opme=0)


def test_load_release_without_extensions(
    conn: psycopg.Connection[TupleRow], tmp_path: Path
) -> None:
    staging = _write_staging(tmp_path / "staging", with_extensions=False)
    report = load_release(conn, staging, "202601")
    assert report == LoadReport(termo=3, medicamento=0, opme=0)
