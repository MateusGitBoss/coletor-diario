-- Consultas de investigação. Rodar no psql ou no editor SQL do Supabase.

-- 1. Últimas execuções de cada fonte, com duração
SELECT f.nome, e.iniciada_em, e.status, e.itens_coletados, e.itens_invalidos,
       e.finalizada_em - e.iniciada_em AS duracao, e.mensagem_erro
  FROM execucoes e JOIN fontes f ON f.id = e.fonte_id
 ORDER BY e.iniciada_em DESC
 LIMIT 20;

-- 2. Fontes que falharam (ou vieram parciais) nas duas últimas execuções seguidas
WITH ordenadas AS (
    SELECT fonte_id, status,
           row_number() OVER (PARTITION BY fonte_id ORDER BY iniciada_em DESC) AS n
      FROM execucoes
     WHERE status <> 'em_andamento'
)
SELECT f.nome
  FROM ordenadas o JOIN fontes f ON f.id = o.fonte_id
 WHERE o.n <= 2
 GROUP BY f.nome
HAVING bool_and(o.status IN ('falha', 'parcial'));

-- 3. Execuções presas em "em_andamento" há mais de 1 hora (processo morreu no meio)
SELECT id, fonte_id, iniciada_em
  FROM execucoes
 WHERE status = 'em_andamento' AND iniciada_em < now() - interval '1 hour';

-- 4. Itens cujo preço variou mais de 20% entre as duas últimas coletas
WITH precos AS (
    SELECT h.item_id, h.preco_centavos, h.coletado_em,
           lag(h.preco_centavos) OVER (PARTITION BY h.item_id ORDER BY h.coletado_em) AS anterior
      FROM historico_precos h
)
SELECT i.titulo, p.anterior, p.preco_centavos,
       round(100.0 * (p.preco_centavos - p.anterior) / p.anterior, 1) AS variacao_pct
  FROM precos p JOIN itens i ON i.id = p.item_id
 WHERE p.anterior IS NOT NULL
   AND abs(p.preco_centavos - p.anterior) > 0.2 * p.anterior
 ORDER BY abs(p.preco_centavos - p.anterior) DESC;

-- 5. Itens que sumiram do site (não foram vistos na última execução bem-sucedida)
SELECT i.fonte_id, i.titulo, i.atualizado_em
  FROM itens i
 WHERE i.atualizado_em < (
        SELECT max(e.iniciada_em) FROM execucoes e
         WHERE e.fonte_id = i.fonte_id AND e.status = 'sucesso'
 );

-- 6. Volume coletado por dia (detecta tendência de queda antes do alerta)
SELECT f.nome, date_trunc('day', e.iniciada_em) AS dia, max(e.itens_coletados) AS itens
  FROM execucoes e JOIN fontes f ON f.id = e.fonte_id
 GROUP BY f.nome, dia
 ORDER BY dia DESC, f.nome;
