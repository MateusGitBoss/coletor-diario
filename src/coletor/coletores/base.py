"""Contrato que todo coletor segue e utilitários compartilhados."""

from typing import Any, Protocol
from urllib.parse import urljoin

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


class Coletor(Protocol):
    """Para adicionar uma fonte nova basta criar uma classe com estes atributos."""

    nome: str
    url_base: str

    def coletar(self) -> list[dict[str, Any]]:
        """Retorna itens brutos. A validação acontece depois, no executor."""
        ...


def erro_transitorio(exc: BaseException) -> bool:
    """Só vale tentar de novo se o erro pode sumir sozinho (rede, 5xx, 429).

    Erro 404 ou HTML diferente do esperado não melhora repetindo.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        codigo = exc.response.status_code
        return codigo >= 500 or codigo == 429
    return False


@retry(
    retry=retry_if_exception(erro_transitorio),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def baixar_html(cliente: httpx.Client, url: str) -> str:
    resposta = cliente.get(url)
    resposta.raise_for_status()
    return resposta.text


def link_proxima_pagina(html: str, url_pagina: str) -> str | None:
    """Os dois sites usam o mesmo padrão de paginação: <li class="next"><a href=...>."""
    link = HTMLParser(html).css_first("li.next a")
    if link is None:
        return None
    href = link.attributes.get("href")
    return urljoin(url_pagina, href) if href else None
