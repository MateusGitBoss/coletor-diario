"""Orquestra uma execução: coleta -> valida -> grava -> avalia -> alerta."""

import logging
import time
from typing import Any

from pydantic import ValidationError

from coletor import repositorio
from coletor.alertas import Notificador
from coletor.anomalia import avaliar_volume
from coletor.coletores.base import Coletor
from coletor.db import DictConnection
from coletor.modelos import ItemColetado, ResumoExecucao

logger = logging.getLogger(__name__)


def validar_itens(brutos: list[dict[str, Any]]) -> tuple[list[ItemColetado], list[str]]:
    """Separa itens bons dos ruins. Item ruim é contado, não derruba a execução."""
    validos: list[ItemColetado] = []
    erros: list[str] = []
    vistos: set[str] = set()
    for bruto in brutos:
        try:
            item = ItemColetado.model_validate(bruto)
        except ValidationError as exc:
            campos = ", ".join(str(e["loc"][0]) for e in exc.errors())
            erros.append(f"{bruto.get('id_externo') or '?'}: campos inválidos ({campos})")
            continue
        if item.id_externo in vistos:  # mesmo item em duas páginas: fica o primeiro
            continue
        vistos.add(item.id_externo)
        validos.append(item)
    return validos, erros


def executar_fonte(
    conn: DictConnection,
    coletor: Coletor,
    notificador: Notificador,
    *,
    limiar: float = 0.5,
    janela: int = 7,
) -> ResumoExecucao:
    fonte_id = repositorio.garantir_fonte(conn, coletor.nome, coletor.url_base)
    execucao_id = repositorio.iniciar_execucao(conn, fonte_id)
    contexto = {"execucao_id": execucao_id, "fonte": coletor.nome}
    logger.info("execução iniciada", extra=contexto)
    inicio = time.monotonic()

    try:
        brutos = coletor.coletar()
    except Exception as exc:
        mensagem = f"{type(exc).__name__}: {exc}"[:2000]
        logger.exception("coleta falhou", extra=contexto)
        repositorio.finalizar_execucao(
            conn,
            execucao_id,
            status="falha",
            itens_coletados=0,
            itens_invalidos=0,
            mensagem_erro=mensagem,
            detalhes={"duracao_segundos": round(time.monotonic() - inicio, 2)},
        )
        resumo = ResumoExecucao(
            execucao_id=execucao_id,
            fonte=coletor.nome,
            status="falha",
            itens_coletados=0,
            itens_invalidos=0,
            mensagem=mensagem,
        )
        notificador.enviar(resumo)
        return resumo

    validos, erros = validar_itens(brutos)
    repositorio.salvar_itens(conn, fonte_id, execucao_id, validos)
    historico = repositorio.volumes_recentes(conn, fonte_id, janela, execucao_id)
    avaliacao = avaliar_volume(len(validos), historico, itens_invalidos=len(erros), limiar=limiar)
    repositorio.finalizar_execucao(
        conn,
        execucao_id,
        status=avaliacao.status,
        itens_coletados=len(validos),
        itens_invalidos=len(erros),
        mensagem_erro=avaliacao.motivo,
        detalhes={
            "duracao_segundos": round(time.monotonic() - inicio, 2),
            "exemplos_invalidos": erros[:5],
            "media_base": historico,
        },
    )
    resumo = ResumoExecucao(
        execucao_id=execucao_id,
        fonte=coletor.nome,
        status=avaliacao.status,
        itens_coletados=len(validos),
        itens_invalidos=len(erros),
        mensagem=avaliacao.motivo,
    )
    logger.info("execução finalizada", extra={**contexto, **resumo.model_dump()})
    if resumo.status != "sucesso":
        notificador.enviar(resumo)
    return resumo
