"""Linha de comando: `coletor migrar`, `coletor executar --todas`, `coletor execucoes`."""

import json
from pathlib import Path
from typing import Annotated

import typer

from coletor.alertas import NotificadorDiscord
from coletor.coletores import criar_coletores
from coletor.config import get_settings
from coletor.db import conectar, migrar
from coletor.executor import executar_fonte
from coletor.logs import configurar_logs
from coletor.repositorio import listar_execucoes, listar_fontes

app = typer.Typer(help="Robô de coleta diária.", no_args_is_help=True)


@app.callback()
def _inicio() -> None:
    configurar_logs(get_settings().nivel_log)


@app.command("migrar")
def cmd_migrar() -> None:
    """Cria/atualiza as tabelas do banco."""
    with conectar(get_settings().database_url) as conn:
        novas = migrar(conn)
    typer.echo(f"{len(novas)} migração(ões) aplicada(s): {', '.join(novas) or '-'}")


@app.command("executar")
def cmd_executar(
    fonte: Annotated[list[str] | None, typer.Option(help="Nome da fonte; pode repetir.")] = None,
    todas: Annotated[bool, typer.Option(help="Executa todas as fontes.")] = False,
    relatorio: Annotated[Path | None, typer.Option(help="Grava um resumo em JSON.")] = None,
) -> None:
    """Executa a coleta. Sai com código 1 se alguma fonte falhar (o agendador fica vermelho)."""
    settings = get_settings()
    coletores = criar_coletores(settings)
    nomes = list(coletores) if todas else (fonte or [])
    desconhecidas = [n for n in nomes if n not in coletores]
    if not nomes or desconhecidas:
        typer.echo(f"Informe --todas ou --fonte entre: {', '.join(coletores)}", err=True)
        raise typer.Exit(2)

    notificador = NotificadorDiscord(settings.discord_webhook_url)
    resumos = []
    with conectar(settings.database_url) as conn:
        conn.autocommit = True  # cada registro de execução é gravado na hora
        migrar(conn)
        for nome in nomes:
            resumo = executar_fonte(
                conn,
                coletores[nome],
                notificador,
                limiar=settings.limiar_anomalia,
                janela=settings.janela_anomalia,
            )
            resumos.append(resumo)
            typer.echo(f"{resumo.fonte:<10} {resumo.status:<8} {resumo.itens_coletados} itens")

    if relatorio:
        relatorio.write_text(
            json.dumps([r.model_dump() for r in resumos], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if any(r.status == "falha" for r in resumos):
        raise typer.Exit(1)


@app.command("execucoes")
def cmd_execucoes(
    ultimas: Annotated[int, typer.Option(help="Quantas mostrar.")] = 10,
    fonte: Annotated[str | None, typer.Option(help="Filtra por fonte.")] = None,
) -> None:
    """Mostra o histórico de execuções (primeiro lugar para investigar falha)."""
    with conectar(get_settings().database_url) as conn:
        linhas = listar_execucoes(conn, fonte, ultimas)
    for e in linhas:
        quando = e["iniciada_em"].strftime("%d/%m %H:%M")
        erro = f"  {e['mensagem_erro']}" if e["mensagem_erro"] else ""
        typer.echo(f"{quando}  {e['fonte']:<10} {e['status']:<12} {e['itens_coletados']:>5}{erro}")


@app.command("fontes")
def cmd_fontes() -> None:
    """Lista as fontes e o estado da última execução de cada uma."""
    with conectar(get_settings().database_url) as conn:
        for f in listar_fontes(conn):
            status = f["ultimo_status"] or "nunca rodou"
            typer.echo(f"{f['nome']:<10} {status:<12} {f['total_itens']} itens")
