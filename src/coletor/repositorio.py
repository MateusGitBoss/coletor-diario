"""Todo o SQL do projeto fica aqui, escrito à mão e parametrizado (%s evita SQL injection)."""

from typing import Any

from psycopg.types.json import Jsonb

from coletor.db import DictConnection
from coletor.modelos import ItemColetado


def garantir_fonte(conn: DictConnection, nome: str, url_base: str) -> int:
    linha = conn.execute(
        """
        INSERT INTO fontes (nome, url_base) VALUES (%s, %s)
        ON CONFLICT (nome) DO UPDATE SET url_base = EXCLUDED.url_base
        RETURNING id
        """,
        (nome, url_base),
    ).fetchone()
    assert linha is not None
    return int(linha["id"])


def iniciar_execucao(conn: DictConnection, fonte_id: int) -> str:
    linha = conn.execute(
        "INSERT INTO execucoes (fonte_id) VALUES (%s) RETURNING id", (fonte_id,)
    ).fetchone()
    assert linha is not None
    return str(linha["id"])


def finalizar_execucao(
    conn: DictConnection,
    execucao_id: str,
    *,
    status: str,
    itens_coletados: int,
    itens_invalidos: int,
    mensagem_erro: str | None = None,
    detalhes: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        UPDATE execucoes
           SET finalizada_em = now(), status = %s, itens_coletados = %s,
               itens_invalidos = %s, mensagem_erro = %s, detalhes = %s
         WHERE id = %s
        """,
        (
            status,
            itens_coletados,
            itens_invalidos,
            mensagem_erro,
            Jsonb(detalhes or {}),
            execucao_id,
        ),
    )


def salvar_itens(
    conn: DictConnection, fonte_id: int, execucao_id: str, itens: list[ItemColetado]
) -> int:
    """Upsert: rodar duas vezes no mesmo dia não duplica nada (idempotente)."""
    with conn.transaction():
        for item in itens:
            linha = conn.execute(
                """
                INSERT INTO itens
                    (fonte_id, id_externo, titulo, url, preco_centavos, em_estoque, dados)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fonte_id, id_externo) DO UPDATE
                   SET titulo = EXCLUDED.titulo,
                       url = EXCLUDED.url,
                       preco_centavos = EXCLUDED.preco_centavos,
                       em_estoque = EXCLUDED.em_estoque,
                       dados = EXCLUDED.dados,
                       atualizado_em = now()
                RETURNING id
                """,
                (
                    fonte_id,
                    item.id_externo,
                    item.titulo,
                    str(item.url),
                    item.preco_centavos,
                    item.em_estoque,
                    Jsonb(item.dados),
                ),
            ).fetchone()
            assert linha is not None
            if item.preco_centavos is not None:
                conn.execute(
                    """
                    INSERT INTO historico_precos (item_id, execucao_id, preco_centavos)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (linha["id"], execucao_id, item.preco_centavos),
                )
    return len(itens)


def volumes_recentes(
    conn: DictConnection, fonte_id: int, janela: int, excluir_execucao: str
) -> list[int]:
    """Quantos itens as últimas execuções bem-sucedidas trouxeram (base da anomalia)."""
    linhas = conn.execute(
        """
        SELECT itens_coletados FROM execucoes
         WHERE fonte_id = %s AND status = 'sucesso' AND id <> %s
         ORDER BY iniciada_em DESC
         LIMIT %s
        """,
        (fonte_id, excluir_execucao, janela),
    ).fetchall()
    return [int(r["itens_coletados"]) for r in linhas]


_SELECT_EXECUCAO = """
    SELECT e.id::text AS id, f.nome AS fonte, e.iniciada_em, e.finalizada_em, e.status,
           e.itens_coletados, e.itens_invalidos, e.mensagem_erro, e.detalhes,
           EXTRACT(EPOCH FROM (e.finalizada_em - e.iniciada_em))::float AS duracao_segundos
      FROM execucoes e JOIN fontes f ON f.id = e.fonte_id
"""


def listar_execucoes(
    conn: DictConnection, fonte: str | None = None, limite: int = 20
) -> list[dict[str, Any]]:
    return conn.execute(
        _SELECT_EXECUCAO
        + " WHERE (%(fonte)s::text IS NULL OR f.nome = %(fonte)s)"
        + " ORDER BY e.iniciada_em DESC LIMIT %(limite)s",
        {"fonte": fonte, "limite": limite},
    ).fetchall()


def obter_execucao(conn: DictConnection, execucao_id: str) -> dict[str, Any] | None:
    return conn.execute(_SELECT_EXECUCAO + " WHERE e.id::text = %s", (execucao_id,)).fetchone()


def listar_fontes(conn: DictConnection) -> list[dict[str, Any]]:
    """Cada fonte com sua última execução (LEFT JOIN LATERAL pega 1 linha por fonte)."""
    return conn.execute(
        """
        SELECT f.nome, f.url_base, f.ativa,
               u.id::text AS ultima_execucao_id, u.status AS ultimo_status,
               u.iniciada_em AS ultima_execucao_em, u.itens_coletados AS ultimos_itens,
               (SELECT count(*) FROM itens i WHERE i.fonte_id = f.id) AS total_itens
          FROM fontes f
          LEFT JOIN LATERAL (
                SELECT * FROM execucoes e WHERE e.fonte_id = f.id
                 ORDER BY e.iniciada_em DESC LIMIT 1
          ) u ON TRUE
         ORDER BY f.nome
        """
    ).fetchall()


def listar_itens(
    conn: DictConnection, fonte: str | None = None, limite: int = 50
) -> list[dict[str, Any]]:
    return conn.execute(
        """
        SELECT i.id, f.nome AS fonte, i.id_externo, i.titulo, i.url, i.preco_centavos,
               i.em_estoque, i.dados, i.atualizado_em
          FROM itens i JOIN fontes f ON f.id = i.fonte_id
         WHERE (%(fonte)s::text IS NULL OR f.nome = %(fonte)s)
         ORDER BY i.atualizado_em DESC, i.id
         LIMIT %(limite)s
        """,
        {"fonte": fonte, "limite": limite},
    ).fetchall()
