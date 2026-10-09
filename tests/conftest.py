import functools
import http.server
import os
import threading
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from coletor.db import DictConnection, conectar, migrar

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def ler_fixture():
    def _ler(nome: str) -> str:
        return (FIXTURES / nome).read_text(encoding="utf-8")

    return _ler


@pytest.fixture
def conn() -> Iterator[DictConnection]:
    """Banco limpo a cada teste. Pula se não houver PostgreSQL configurado."""
    url = os.environ.get("DATABASE_URL_TESTE")
    if not url:
        pytest.skip("DATABASE_URL_TESTE não definido")
    try:
        conexao = conectar(url)
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL indisponível: {exc}")
    conexao.autocommit = True
    conexao.execute("DROP SCHEMA public CASCADE")
    conexao.execute("CREATE SCHEMA public")
    migrar(conexao)
    yield conexao
    conexao.close()


@pytest.fixture(scope="session")
def servidor_local() -> Iterator[str]:
    """Servidor HTTP local servindo tests/fixtures, para testar o navegador sem internet."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURES))
    handler.log_message = lambda *args: None  # type: ignore[attr-defined]
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()
