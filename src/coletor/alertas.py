"""Envio de alertas para um canal do Discord via webhook."""

import logging
from typing import Protocol

import httpx

from coletor.modelos import ResumoExecucao

logger = logging.getLogger(__name__)

_CORES = {"sucesso": 0x2E7D32, "parcial": 0xF9A825, "falha": 0xC62828}


class Notificador(Protocol):
    def enviar(self, resumo: ResumoExecucao) -> bool: ...


def montar_mensagem(resumo: ResumoExecucao) -> dict[str, object]:
    return {
        "username": "coletor-diario",
        "embeds": [
            {
                "title": f"Coleta {resumo.fonte}: {resumo.status.upper()}",
                "description": resumo.mensagem or "Sem detalhes.",
                "color": _CORES[resumo.status],
                "fields": [
                    {"name": "Itens válidos", "value": str(resumo.itens_coletados), "inline": True},
                    {"name": "Inválidos", "value": str(resumo.itens_invalidos), "inline": True},
                ],
                "footer": {"text": f"execução {resumo.execucao_id}"},
            }
        ],
    }


class NotificadorDiscord:
    def __init__(self, webhook_url: str, cliente: httpx.Client | None = None) -> None:
        self._url = webhook_url
        self._cliente = cliente or httpx.Client(timeout=10)

    def enviar(self, resumo: ResumoExecucao) -> bool:
        """Nunca levanta exceção: alerta que falha não pode derrubar a coleta."""
        if not self._url:
            logger.warning(
                "alerta não enviado: DISCORD_WEBHOOK_URL vazio", extra=resumo.model_dump()
            )
            return False
        try:
            resposta = self._cliente.post(self._url, json=montar_mensagem(resumo))
            resposta.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.exception("falha ao enviar alerta ao Discord", extra={"fonte": resumo.fonte})
            return False
