import pytest

from coletor.coletores.citacoes import ColetorCitacoes, extrair_citacoes


def test_extrai_citacoes_do_html_renderizado(ler_fixture):
    url = "https://quotes.toscrape.com/js/"
    citacoes = extrair_citacoes(ler_fixture("citacoes_renderizada.html"), url)

    assert len(citacoes) == 2
    assert citacoes[0]["titulo"].startswith("The world as we have created it")
    assert citacoes[0]["dados"] == {
        "autor": "Albert Einstein",
        "tags": ["change", "deep-thoughts", "thinking"],
    }
    assert len(citacoes[0]["id_externo"]) == 16


def test_id_da_citacao_e_estavel(ler_fixture):
    html = ler_fixture("citacoes_renderizada.html")
    url = "https://quotes.toscrape.com/js/"
    assert (
        extrair_citacoes(html, url)[0]["id_externo"] == extrair_citacoes(html, url)[0]["id_externo"]
    )


def _navegador_disponivel() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


precisa_navegador = pytest.mark.skipif(
    not _navegador_disponivel(), reason="Chromium do Playwright não instalado"
)


@precisa_navegador
def test_coleta_pagina_que_depende_de_javascript(servidor_local, tmp_path):
    coletor = ColetorCitacoes(url_inicial=f"{servidor_local}/js/", artefatos_dir=str(tmp_path))
    itens = coletor.coletar()

    assert [i["dados"]["autor"] for i in itens] == [
        "Steve Martin",
        "Albert Einstein",
        "Leonardo da Vinci",
    ]


@precisa_navegador
def test_falha_salva_print_e_html_para_investigar(servidor_local, tmp_path):
    coletor = ColetorCitacoes(
        url_inicial=f"{servidor_local}/quebrado/", artefatos_dir=str(tmp_path), timeout_ms=1000
    )
    with pytest.raises(Exception, match="Timeout"):
        coletor.coletar()

    arquivos = sorted(p.suffix for p in tmp_path.iterdir())
    assert arquivos == [".html", ".png"]
