# Roteiro de estudo para entrevista

Para cada pergunta: a resposta curta que você deve conseguir dar de cabeça e onde está no código.

## 1. Explique o projeto em 1 minuto

"É um robô que coleta dados de dois sites todo dia às 6h pelo GitHub Actions. Um site é estático e eu coleto com HTTP; o outro monta a página com JavaScript, então uso Playwright. Cada item passa por validação com Pydantic e é gravado no Postgres com upsert, então rodar duas vezes não duplica. Cada execução vira uma linha numa tabela com status, quantidade e erro. Se falhar ou vier menos da metade do normal, manda alerta no Discord. Quando o navegador falha, salvo print e HTML da tela para investigar."

## 2. Perguntas técnicas

**Quando usar requests/httpx e quando usar Playwright?**
Se o dado está no HTML que o servidor devolve, HTTP basta: é rápido e leve. Se o dado só aparece depois que o JavaScript roda, preciso de navegador. Teste prático: ver o código-fonte da página (Ctrl+U); se o dado não está lá, é JavaScript. Navegador gasta mais memória e tempo, então só uso onde é obrigatório. → `coletores/livros.py` x `coletores/citacoes.py`

**Como você sabe que o robô falhou se ele não deu erro?**
Pelo volume. Se o site muda o HTML, o parser pode não achar nada e a execução "termina bem" com 3 itens. Comparo com a média das últimas execuções boas: abaixo de 50% vira `parcial` e alerta. Também conto itens inválidos: acima de 10% é sinal de mudança no layout. → `anomalia.py`

**O que é idempotência e por que importa aqui?**
Operação idempotente dá o mesmo resultado se repetida. O agendador pode rodar duas vezes, ou eu posso rodar à mão para corrigir algo. Com `INSERT ... ON CONFLICT (fonte_id, id_externo) DO UPDATE` o item é atualizado em vez de duplicado. → `repositorio.salvar_itens`

**Por que preço em centavos?**
Float é binário e não representa 0,10 exatamente; somas acumulam erro. Inteiro em centavos é exato. Outra opção seria `NUMERIC` no banco e `Decimal` no Python.

**O site mudou o HTML. O que acontece e como você investiga?**
1) Chega alerta no Discord com status e motivo. 2) `coletor execucoes` ou a consulta 1 de `docs/consultas.sql` mostra quando começou. 3) O campo `detalhes` da execução traz exemplos de itens inválidos e o motivo. 4) No Playwright, o artefato do GitHub Actions tem print e HTML do momento. 5) Ajusto o seletor, salvo o HTML novo como fixture, escrevo o teste que reproduz e corrijo.

**Retry: em que erro faz sentido?**
Em erro transitório: falha de rede, timeout, 5xx, 429 (limite de requisições). Uso backoff exponencial (1s, 2s, 4s) para não martelar um servidor que já está com problema. Não faz sentido em 404 ou em erro de parsing, porque repetir dá o mesmo resultado. → `coletores/base.py`

**Por que validar com Pydantic?**
Dado de site externo não é confiável. Pydantic garante tipo e formato (URL válida, preço não negativo, id não vazio). Item inválido é contado e registrado, não derruba os outros 999.

**Por que GitHub Actions como agendador? Limites?**
É grátis, tem log e histórico de cada execução e não exige servidor. Limites: o cron pode atrasar minutos, a execução tem tempo máximo e não serve para tarefas muito frequentes. Para isso usaria cron numa VPS Linux, um worker no Railway ou uma fila.

**Como os testes funcionam sem internet?**
HTML real salvo em `tests/fixtures`. Para o Playwright subo um servidor HTTP local com uma página que monta o conteúdo via JavaScript, igual ao site real. Testes de banco recriam o schema a cada teste.

**SQL: explique a consulta das fontes com última execução.**
`LEFT JOIN LATERAL` executa uma subconsulta por fonte que pega só a execução mais recente (`ORDER BY ... LIMIT 1`). `LEFT` porque uma fonte nova ainda não tem execução. → `repositorio.listar_fontes`

**Scraping é legal?**
Depende. Respeitar `robots.txt` e os termos de uso, não coletar dado pessoal, limitar a frequência (aqui há pausa entre páginas) e se identificar no User-Agent. Os sites deste projeto existem para treino.

## 3. Perguntas de comportamento

**Conte um problema que você investigou até a causa raiz.** Use o fluxo da pergunta "O site mudou o HTML" com um caso real seu da construtora ou da lavanderia.

**Como você usa IA no trabalho?** Uso o Claude Code para escrever código, sempre por pull request, revisando o diff, rodando os testes e entendendo cada decisão antes de aceitar. Este roteiro é parte disso.

## 4. Para praticar

1. Rode `coletor executar --fonte livros` e veja a linha nova em `execucoes`.
2. Troque o seletor `article.product_pod` por outro e rode de novo: veja o status virar `falha` e o alerta.
3. Mude `LIMIAR_ANOMALIA` para 0.9 e rode 4 vezes; explique o resultado.
4. Escreva uma consulta nova: os 5 livros mais caros em estoque.
