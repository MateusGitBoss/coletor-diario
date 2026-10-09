import json

import httpx

from coletor.alertas import NotificadorDiscord, montar_mensagem
from coletor.modelos import ResumoExecucao

RESUMO = ResumoExecucao(
    execucao_id="abc",
    fonte="livros",
    status="parcial",
    itens_coletados=20,
    itens_invalidos=0,
    mensagem="coletou 20 itens, abaixo de 50% da média recente (1000)",
)


def test_mensagem_tem_status_e_motivo():
    embed = montar_mensagem(RESUMO)["embeds"][0]  # type: ignore[index]
    assert "PARCIAL" in embed["title"]
    assert "abaixo de 50%" in embed["description"]


def test_envia_para_o_webhook():
    recebidos: list[dict] = []

    def responder(request: httpx.Request) -> httpx.Response:
        recebidos.append(json.loads(request.content))
        return httpx.Response(204)

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    assert NotificadorDiscord("https://discord.test/webhook", cliente).enviar(RESUMO)
    assert recebidos[0]["username"] == "coletor-diario"


def test_discord_fora_do_ar_nao_levanta_excecao():
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    assert NotificadorDiscord("https://discord.test/webhook", cliente).enviar(RESUMO) is False


def test_sem_webhook_configurado_so_registra_no_log():
    assert NotificadorDiscord("").enviar(RESUMO) is False
