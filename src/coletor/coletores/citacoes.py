"""Coletor de citações em https://quotes.toscrape.com/js/.

Esta versão do site monta o conteúdo com JavaScript: um GET simples devolve a página
sem as citações. Por isso aqui usamos um navegador de verdade (Playwright).
Navegador é ~10x mais lento e pesado que HTTP puro, então só usamos onde precisa.
"""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from coletor.coletores.base import link_proxima_pagina

logger = logging.getLogger(__name__)

URL_INICIAL = "https://quotes.toscrape.com/js/"


def _id_citacao(autor: str, texto: str) -> str:
    # O site não tem id próprio: geramos um estável a partir do conteúdo
    return hashlib.sha1(f"{autor}|{texto}".encode()).hexdigest()[:16]


def extrair_citacoes(html: str, url_pagina: str) -> list[dict[str, Any]]:
    itens: list[dict[str, Any]] = []
    for bloco in HTMLParser(html).css("div.quote"):
        texto_no = bloco.css_first("span.text")
        autor_no = bloco.css_first("small.author")
        texto = texto_no.text(strip=True).strip('“”"') if texto_no else ""
        autor = autor_no.text(strip=True) if autor_no else ""
        itens.append(
            {
                "id_externo": _id_citacao(autor, texto) if texto else "",
                "titulo": texto,
                "url": url_pagina,
                "dados": {"autor": autor, "tags": [t.text(strip=True) for t in bloco.css("a.tag")]},
            }
        )
    return itens


class ColetorCitacoes:
    nome = "citacoes"
    url_base = "https://quotes.toscrape.com/js/"

    def __init__(
        self,
        url_inicial: str = URL_INICIAL,
        artefatos_dir: str = "artefatos",
        max_paginas: int = 20,
        timeout_ms: int = 15_000,
    ) -> None:
        self._url_inicial = url_inicial
        self._artefatos = Path(artefatos_dir)
        self._max_paginas = max_paginas
        self._timeout_ms = timeout_ms

    def coletar(self) -> list[dict[str, Any]]:
        # Import aqui dentro: quem não usa este coletor não precisa do navegador instalado
        from playwright.sync_api import sync_playwright

        itens: list[dict[str, Any]] = []
        paginas = 0
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page()
            try:
                url: str | None = self._url_inicial
                while url and paginas < self._max_paginas:
                    pagina.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                    # Espera o JavaScript desenhar as citações; se não aparecer, é falha
                    pagina.wait_for_selector("div.quote", timeout=self._timeout_ms)
                    html = pagina.content()
                    itens.extend(extrair_citacoes(html, url))
                    url = link_proxima_pagina(html, url)
                    paginas += 1
            except Exception:
                self._salvar_evidencias(pagina)
                raise
            finally:
                navegador.close()
        logger.info("citações coletadas", extra={"paginas": paginas, "itens": len(itens)})
        return itens

    def _salvar_evidencias(self, pagina: Any) -> None:
        """Print e HTML da tela no momento da falha: é a primeira coisa a olhar."""
        try:
            self._artefatos.mkdir(parents=True, exist_ok=True)
            carimbo = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            base = self._artefatos / f"{self.nome}-{carimbo}"
            pagina.screenshot(path=f"{base}.png", full_page=True)
            Path(f"{base}.html").write_text(pagina.content(), encoding="utf-8")
            logger.warning("evidências da falha salvas", extra={"arquivo": str(base)})
        except Exception:
            logger.exception("não foi possível salvar evidências da falha")
