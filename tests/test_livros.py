import httpx
import pytest
from tenacity import wait_none

from coletor.coletores.base import baixar_html, erro_transitorio, link_proxima_pagina
from coletor.coletores.livros import ColetorLivros, extrair_livros, preco_para_centavos

URL = "https://books.toscrape.com/catalogue/page-1.html"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("£51.77", 5177), ("Â£53.74", 5374), ("£0.99", 99), ("R$ 10,50", 1050), ("grátis", None)],
)
def test_preco_para_centavos(texto, esperado):
    assert preco_para_centavos(texto) == esperado


def test_extrai_livros_da_pagina(ler_fixture):
    livros = extrair_livros(ler_fixture("livros_pagina1.html"), URL)

    assert len(livros) == 3
    primeiro = livros[0]
    assert primeiro["id_externo"] == "a-light-in-the-attic_1000"
    assert primeiro["titulo"] == "A Light in the Attic"  # título completo, não o truncado
    assert (
        primeiro["url"]
        == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    )
    assert primeiro["preco_centavos"] == 5177
    assert primeiro["em_estoque"] is True
    assert primeiro["dados"]["estrelas"] == 3


def test_livro_sem_link_sai_com_id_vazio_para_ser_rejeitado_na_validacao(ler_fixture):
    livros = extrair_livros(ler_fixture("livros_pagina1.html"), URL)
    assert livros[2]["id_externo"] == ""
    assert livros[2]["em_estoque"] is False


def test_paginacao(ler_fixture):
    proxima = link_proxima_pagina(ler_fixture("livros_pagina1.html"), URL)
    assert proxima == "https://books.toscrape.com/catalogue/page-2.html"
    assert link_proxima_pagina(ler_fixture("livros_ultima.html"), URL) is None


def test_coletor_percorre_todas_as_paginas(ler_fixture):
    paginas = {
        "/catalogue/page-1.html": ler_fixture("livros_pagina1.html"),
        "/catalogue/page-2.html": ler_fixture("livros_ultima.html"),
    }

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=paginas[request.url.path])

    coletor = ColetorLivros(
        cliente=httpx.Client(transport=httpx.MockTransport(responder)), pausa_segundos=0
    )
    itens = coletor.coletar()

    assert len(itens) == 4
    assert itens[-1]["id_externo"] == "1000-places-to-see-before-you-die_1"


def test_tenta_de_novo_em_erro_de_servidor():
    chamadas = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        return httpx.Response(503 if chamadas["n"] < 3 else 200, text="ok")

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    assert baixar_html.retry_with(wait=wait_none())(cliente, "https://x.test/") == "ok"
    assert chamadas["n"] == 3


def test_nao_tenta_de_novo_em_404():
    chamadas = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        return httpx.Response(404)

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    with pytest.raises(httpx.HTTPStatusError):
        baixar_html.retry_with(wait=wait_none())(cliente, "https://x.test/")
    assert chamadas["n"] == 1


def test_classificacao_de_erro_transitorio():
    req = httpx.Request("GET", "https://x.test")
    assert erro_transitorio(httpx.ConnectTimeout("lento"))
    assert erro_transitorio(httpx.HTTPStatusError("", request=req, response=httpx.Response(429)))
    assert not erro_transitorio(
        httpx.HTTPStatusError("", request=req, response=httpx.Response(404))
    )
    assert not erro_transitorio(ValueError("html mudou"))
