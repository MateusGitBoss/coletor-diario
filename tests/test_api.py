import pytest
from fastapi.testclient import TestClient

from coletor.api import app, obter_conexao
from coletor.executor import executar_fonte
from tests.test_executor import ColetorFalso, NotificadorFalso, _itens

pytestmark = pytest.mark.banco


@pytest.fixture
def cliente(conn):
    app.dependency_overrides[obter_conexao] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_fontes_e_execucoes(cliente, conn):
    resumo = executar_fonte(conn, ColetorFalso(_itens(3)), NotificadorFalso())

    fontes = cliente.get("/fontes").json()
    assert fontes[0]["nome"] == "falso" and fontes[0]["ultimo_status"] == "sucesso"

    lista = cliente.get("/execucoes", params={"fonte": "falso"}).json()
    assert [e["id"] for e in lista] == [resumo.execucao_id]

    detalhe = cliente.get(f"/execucoes/{resumo.execucao_id}").json()
    assert detalhe["itens_coletados"] == 3
    assert detalhe["duracao_segundos"] >= 0


def test_execucao_inexistente_da_404(cliente):
    resposta = cliente.get("/execucoes/00000000-0000-0000-0000-000000000000")
    assert resposta.status_code == 404


def test_itens_respeita_limite(cliente, conn):
    executar_fonte(conn, ColetorFalso(_itens(5)), NotificadorFalso())
    assert len(cliente.get("/itens", params={"limite": 2}).json()) == 2
    assert cliente.get("/itens", params={"limite": 0}).status_code == 422
