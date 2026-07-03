import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import TupleRow

_DEFAULT_DSN = "postgres://tuss:tuss@localhost:5432/tuss"
_MIGRATION = Path("migrations/0001_terminologias")


def _run_script(connection: psycopg.Connection[TupleRow], path: Path) -> None:
    for statement in path.read_text().split(";"):
        if statement.strip():
            connection.execute(statement.encode())
    connection.commit()


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[TupleRow]]:
    """Conexão com o Postgres de teste, com o schema reaplicado do zero.

    Pula o teste se o banco estiver indisponível, mantendo a suíte verde sem
    Docker de pé.
    """
    dsn = os.environ.get("TUSS_TEST_DSN", _DEFAULT_DSN)
    try:
        connection = psycopg.connect(dsn, connect_timeout=2)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL de teste indisponível")
    _run_script(connection, _MIGRATION.with_suffix(".down.sql"))
    _run_script(connection, _MIGRATION.with_suffix(".up.sql"))
    yield connection
    connection.close()
