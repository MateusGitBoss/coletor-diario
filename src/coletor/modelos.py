"""Modelos de dados validados com Pydantic."""

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

Status = Literal["sucesso", "parcial", "falha"]


class ItemColetado(BaseModel):
    """Um item extraído de uma página. Tudo que vem do site é validado aqui."""

    id_externo: str = Field(min_length=1, max_length=300)
    titulo: str = Field(min_length=1)
    url: HttpUrl
    preco_centavos: int | None = Field(default=None, ge=0)
    em_estoque: bool | None = None
    dados: dict[str, Any] = Field(default_factory=dict)


class ResumoExecucao(BaseModel):
    execucao_id: str
    fonte: str
    status: Status
    itens_coletados: int
    itens_invalidos: int
    mensagem: str | None = None
