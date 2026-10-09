"""Coletor de livros em https://books.toscrape.com (HTML estático, sem navegador)."""

import logging
import re
import time
from typing import Any
from urllib.parse import urljoin

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import LexborNode as Node

from coletor.coletores.base import baixar_html, link_proxima_pagina

logger = logging.getLogger(__name__)

URL_INICIAL = "https://books.toscrape.com/catalogue/page-1.html"
_PRECO = re.compile(r"(\d+)[.,](\d{2})")
_ESTRELAS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def preco_para_centavos(texto: str) -> int | None:
    """'£51.77' -> 5177. Dinheiro em inteiro evita erro de arredondamento de float."""
    achado = _PRECO.search(texto)
    if not achado:
        return None
    return int(achado.group(1)) * 100 + int(achado.group(2))


def _id_pela_url(url: str) -> str:
    # .../catalogue/a-light-in-the-attic_1000/index.html -> a-light-in-the-attic_1000
    partes = [p for p in url.split("/") if p and p != "index.html"]
    return partes[-1] if partes else ""


def _extrair_livro(card: Node, url_pagina: str) -> dict[str, Any]:
    link = card.css_first("h3 a")
    href = (link.attributes.get("href") or "") if link else ""
    url = urljoin(url_pagina, href) if href else ""
    preco = card.css_first("p.price_color")
    estoque = card.css_first("p.availability")
    estrelas = card.css_first("p.star-rating")
    classes = (estrelas.attributes.get("class") or "").split() if estrelas else []
    estrelas_num = next((_ESTRELAS[c] for c in classes if c in _ESTRELAS), None)
    return {
        "id_externo": _id_pela_url(href) if href else "",
        "titulo": (link.attributes.get("title") or link.text(strip=True)) if link else "",
        "url": url,
        "preco_centavos": preco_para_centavos(preco.text()) if preco else None,
        "em_estoque": ("in stock" in estoque.text().lower()) if estoque else None,
        "dados": {"moeda": "GBP", "estrelas": estrelas_num},
    }


def extrair_livros(html: str, url_pagina: str) -> list[dict[str, Any]]:
    cards = HTMLParser(html).css("article.product_pod")
    return [_extrair_livro(card, url_pagina) for card in cards]


class ColetorLivros:
    nome = "livros"
    url_base = "https://books.toscrape.com"

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        url_inicial: str = URL_INICIAL,
        max_paginas: int = 60,
        pausa_segundos: float = 0.3,
        timeout_segundos: float = 20.0,
    ) -> None:
        self._cliente = cliente or httpx.Client(
            timeout=timeout_segundos,
            headers={"User-Agent": "coletor-diario (projeto de portfolio)"},
            follow_redirects=True,
        )
        self._url_inicial = url_inicial
        self._max_paginas = max_paginas
        self._pausa = pausa_segundos

    def coletar(self) -> list[dict[str, Any]]:
        itens: list[dict[str, Any]] = []
        url: str | None = self._url_inicial
        paginas = 0
        with self._cliente as cliente:
            while url and paginas < self._max_paginas:
                html = baixar_html(cliente, url)
                novos = extrair_livros(html, url)
                logger.debug("página coletada", extra={"url": url, "itens": len(novos)})
                itens.extend(novos)
                url = link_proxima_pagina(html, url)
                paginas += 1
                if url and self._pausa:
                    time.sleep(self._pausa)  # educação com o site: não martelar o servidor
        logger.info("livros coletados", extra={"paginas": paginas, "itens": len(itens)})
        return itens
