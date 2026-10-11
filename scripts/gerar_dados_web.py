"""Gera os dados da demonstração web (web/dados/demo.json) com o código de verdade.

A página em web/ é estática e não roda Python. Este script:
1. passa os HTML salvos em tests/fixtures pelos mesmos extratores e pela mesma validação
   da coleta real, para mostrar o que o robô extrai (e o que ele recusa);
2. roda avaliar_volume() numa lista de casos e grava a resposta. A página refaz a regra em
   JavaScript para o simulador e confere, caso a caso, se chega no mesmo resultado.

    uv run python scripts/gerar_dados_web.py
"""

import json
from pathlib import Path
from typing import Any

from coletor.anomalia import avaliar_volume
from coletor.coletores.citacoes import extrair_citacoes
from coletor.coletores.livros import extrair_livros
from coletor.executor import validar_itens

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
SAIDA = RAIZ / "web" / "dados" / "demo.json"

PAGINAS = [
    ("livros", "livros_pagina1.html", "https://books.toscrape.com/catalogue/page-1.html"),
    ("livros", "livros_ultima.html", "https://books.toscrape.com/catalogue/page-50.html"),
    ("livros", "quebrado/index.html", "https://books.toscrape.com/catalogue/page-1.html"),
    ("citacoes", "citacoes_renderizada.html", "https://quotes.toscrape.com/js/"),
]

# (itens válidos, itens inválidos, histórico das últimas execuções boas)
CASOS_ANOMALIA: list[tuple[str, int, int, list[int]]] = [
    ("Dia normal", 1000, 0, [1000, 1000, 998, 1000, 1000, 1000, 1000]),
    ("Site mudou o HTML", 3, 0, [1000, 1000, 998, 1000, 1000, 1000, 1000]),
    ("Muitos itens inválidos", 900, 120, [1000, 1000, 998, 1000, 1000, 1000, 1000]),
    ("Site fora do ar", 0, 0, [1000, 1000, 998, 1000, 1000, 1000, 1000]),
    ("Primeiras execuções", 40, 0, [1000, 1000]),
    ("Queda moderada", 600, 10, [1000, 1000, 998, 1000, 1000, 1000, 1000]),
    ("Exatamente metade", 500, 0, [1000, 1000, 1000]),
    ("Pouco abaixo da metade", 499, 0, [1000, 1000, 1000]),
    ("10% inválidos", 90, 10, [100, 100, 100]),
    ("11% inválidos", 89, 11, [100, 100, 100]),
]


def main() -> None:
    paginas: list[dict[str, Any]] = []
    for fonte, arquivo, url in PAGINAS:
        html = (FIXTURES / arquivo).read_text(encoding="utf-8")
        brutos = extrair_livros(html, url) if fonte == "livros" else extrair_citacoes(html, url)
        validos, erros = validar_itens(brutos)
        paginas.append(
            {
                "fonte": fonte,
                "arquivo": f"tests/fixtures/{arquivo}",
                "extraidos": len(brutos),
                "validos": [item.model_dump(mode="json") for item in validos],
                "erros": erros,
            }
        )

    casos = []
    for nome, validos_n, invalidos_n, historico in CASOS_ANOMALIA:
        resultado = avaliar_volume(validos_n, historico, itens_invalidos=invalidos_n)
        casos.append(
            {
                "nome": nome,
                "validos": validos_n,
                "invalidos": invalidos_n,
                "historico": historico,
                "status": resultado.status,
                "motivo": resultado.motivo,
            }
        )

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps({"paginas": paginas, "casos_anomalia": casos}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{len(paginas)} páginas, {len(casos)} casos -> {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
