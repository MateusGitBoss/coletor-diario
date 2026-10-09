"""API somente leitura sobre o banco do coletor. Consumida pelo painel React."""

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from coletor import repositorio
from coletor.config import get_settings
from coletor.db import DictConnection, conectar

settings = get_settings()
app = FastAPI(
    title="coletor-diario",
    description="Histórico das execuções do robô de coleta e itens coletados.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.lista_cors_origens,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def obter_conexao() -> Iterator[DictConnection]:
    """Uma conexão por requisição, sempre fechada no final (mesmo com erro)."""
    with conectar(get_settings().database_url) as conn:
        yield conn


Conexao = Annotated[DictConnection, Depends(obter_conexao)]


@app.get("/saude")
def saude(conn: Conexao) -> dict[str, str]:
    conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/fontes")
def fontes(conn: Conexao) -> list[dict[str, Any]]:
    return repositorio.listar_fontes(conn)


@app.get("/execucoes")
def execucoes(
    conn: Conexao,
    fonte: str | None = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 20,
) -> list[dict[str, Any]]:
    return repositorio.listar_execucoes(conn, fonte, limite)


@app.get("/execucoes/{execucao_id}")
def execucao(execucao_id: str, conn: Conexao) -> dict[str, Any]:
    encontrada = repositorio.obter_execucao(conn, execucao_id)
    if encontrada is None:
        raise HTTPException(status_code=404, detail="execução não encontrada")
    return encontrada


@app.get("/itens")
def itens(
    conn: Conexao,
    fonte: str | None = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[dict[str, Any]]:
    return repositorio.listar_itens(conn, fonte, limite)
