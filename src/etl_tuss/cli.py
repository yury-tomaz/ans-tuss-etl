"""Entrypoint de linha de comando do pipeline TUSS.

Encadeia a extração de um release para o staging e a carga idempotente no
PostgreSQL. Não migra o schema — isso é um passo separado (ADR 0007).
"""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import psycopg

from etl_tuss.postgres_loader import UpsertResult
from etl_tuss.release_extractor import extract_release
from etl_tuss.release_loader import LoadReport, load_release

_DEFAULT_STAGING = Path("staging")
_DEFAULT_DSN = "postgres://tuss:tuss@localhost:5432/tuss"


def main(argv: Sequence[str] | None = None) -> int:
    """Extrai o release para o staging e carrega no PostgreSQL."""
    args = _parse_args(argv)
    try:
        report = _run_pipeline(args.release_dir, args.staging, args.versao, args.dsn)
    except ValueError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 1
    print(_format_report(args.versao, report))
    return 0


def _run_pipeline(release_dir: Path, staging: Path, versao: str, dsn: str) -> LoadReport:
    extract_release(release_dir, staging, versao)
    with psycopg.connect(dsn) as conn:
        return load_release(conn, staging, versao)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="etl-tuss", description="Extrai e carrega um release TUSS."
    )
    parser.add_argument("release_dir", type=Path, help="diretório do release da ANS")
    parser.add_argument("versao", help="versão do release (ex.: 202601)")
    parser.add_argument(
        "--staging", type=Path, default=_DEFAULT_STAGING, help="raiz do staging Parquet"
    )
    parser.add_argument("--dsn", default=_default_dsn(), help="DSN do PostgreSQL")
    return parser.parse_args(argv)


def _default_dsn() -> str:
    return os.environ.get("TUSS_DSN", _DEFAULT_DSN)


def _format_report(versao: str, report: LoadReport) -> str:
    linhas = [
        f"versao={versao} carregada:",
        _format_line("termo", report.termo),
        _format_line("medicamento", report.medicamento),
        _format_line("opme", report.opme),
    ]
    return "\n".join(linhas)


def _format_line(nome: str, resultado: UpsertResult) -> str:
    return (
        f"  {nome}: {resultado.inserted} inseridas, "
        f"{resultado.updated} atualizadas, {resultado.unchanged} inalteradas"
    )
