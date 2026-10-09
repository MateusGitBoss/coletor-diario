from typing import Any

import pytest

from coletor import repositorio
from coletor.executor import executar_fonte, validar_itens
from coletor.modelos import ResumoExecucao

pytestmark = pytest.mark.banco


class ColetorFalso:
    nome = "falso"
    url_base = "https://falso.test"

    def __init__(self, itens: list[dict[str, Any]] | None = None, erro: Exception | None = None):
        self.itens = itens or []
        self.erro = erro

    def coletar(self) -> list[dict[str, Any]]:
        if self.erro:
            raise self.erro
        return self.itens


class NotificadorFalso:
    def __init__(self) -> None:
        self.enviados: list[ResumoExecucao] = []

    def enviar(self, resumo: ResumoExecucao) -> bool:
        self.enviados.append(resumo)
        return True


def _itens(n: int, preco: int = 1000) -> list[dict[str, Any]]:
    return [
        {
            "id_externo": f"item-{i}",
            "titulo": f"Item {i}",
            "url": f"https://falso.test/{i}",
            "preco_centavos": preco,
        }
        for i in range(n)
    ]


def test_validacao_separa_invalidos_e_remove_duplicados():
    brutos = [*_itens(2), {"id_externo": "", "titulo": "x", "url": "nao-e-url"}, _itens(1)[0]]
    validos, erros = validar_itens(brutos)
    assert [v.id_externo for v in validos] == ["item-0", "item-1"]
    assert len(erros) == 1 and "id_externo" in erros[0] and "url" in erros[0]


def test_execucao_com_sucesso_grava_itens_e_nao_alerta(conn):
    notificador = NotificadorFalso()
    resumo = executar_fonte(conn, ColetorFalso(_itens(10)), notificador)

    assert resumo.status == "sucesso"
    assert resumo.itens_coletados == 10
    assert notificador.enviados == []
    execucao = repositorio.obter_execucao(conn, resumo.execucao_id)
    assert execucao is not None and execucao["status"] == "sucesso"
    assert execucao["finalizada_em"] is not None


def test_rodar_duas_vezes_nao_duplica_itens_mas_guarda_historico_de_preco(conn):
    executar_fonte(conn, ColetorFalso(_itens(5, preco=1000)), NotificadorFalso())
    executar_fonte(conn, ColetorFalso(_itens(5, preco=1200)), NotificadorFalso())

    assert conn.execute("SELECT count(*) AS n FROM itens").fetchone()["n"] == 5
    assert conn.execute("SELECT count(*) AS n FROM historico_precos").fetchone()["n"] == 10
    precos = {r["preco_centavos"] for r in conn.execute("SELECT preco_centavos FROM itens")}
    assert precos == {1200}


def test_erro_na_coleta_registra_falha_e_alerta(conn):
    notificador = NotificadorFalso()
    resumo = executar_fonte(conn, ColetorFalso(erro=TimeoutError("site lento")), notificador)

    assert resumo.status == "falha"
    assert "TimeoutError: site lento" in (resumo.mensagem or "")
    assert len(notificador.enviados) == 1
    execucao = repositorio.obter_execucao(conn, resumo.execucao_id)
    assert execucao is not None and execucao["mensagem_erro"].startswith("TimeoutError")


def test_queda_de_volume_gera_parcial_e_alerta(conn):
    for _ in range(3):
        executar_fonte(conn, ColetorFalso(_itens(100)), NotificadorFalso())

    notificador = NotificadorFalso()
    resumo = executar_fonte(conn, ColetorFalso(_itens(10)), notificador)

    assert resumo.status == "parcial"
    assert [r.status for r in notificador.enviados] == ["parcial"]


def test_consultas_de_leitura(conn):
    executar_fonte(conn, ColetorFalso(_itens(3)), NotificadorFalso())

    fontes = repositorio.listar_fontes(conn)
    assert fontes[0]["nome"] == "falso"
    assert fontes[0]["ultimo_status"] == "sucesso"
    assert fontes[0]["total_itens"] == 3
    assert len(repositorio.listar_execucoes(conn, fonte="falso")) == 1
    assert repositorio.listar_execucoes(conn, fonte="outra") == []
    assert len(repositorio.listar_itens(conn, fonte="falso", limite=2)) == 2
