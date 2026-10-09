-- Fontes de dados que o robô sabe coletar
CREATE TABLE fontes (
    id          SERIAL PRIMARY KEY,
    nome        TEXT NOT NULL UNIQUE,
    url_base    TEXT NOT NULL,
    ativa       BOOLEAN NOT NULL DEFAULT TRUE,
    criada_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Uma linha por execução do robô: é aqui que se investiga falha
CREATE TABLE execucoes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fonte_id          INTEGER NOT NULL REFERENCES fontes(id),
    iniciada_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizada_em     TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'em_andamento'
                      CHECK (status IN ('em_andamento', 'sucesso', 'parcial', 'falha')),
    itens_coletados   INTEGER NOT NULL DEFAULT 0,
    itens_invalidos   INTEGER NOT NULL DEFAULT 0,
    mensagem_erro     TEXT,
    detalhes          JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX idx_execucoes_fonte_data ON execucoes (fonte_id, iniciada_em DESC);

-- Estado atual de cada item coletado (livro, citação...)
CREATE TABLE itens (
    id                BIGSERIAL PRIMARY KEY,
    fonte_id          INTEGER NOT NULL REFERENCES fontes(id),
    id_externo        TEXT NOT NULL,
    titulo            TEXT NOT NULL,
    url               TEXT NOT NULL,
    preco_centavos    INTEGER CHECK (preco_centavos >= 0),
    em_estoque        BOOLEAN,
    dados             JSONB NOT NULL DEFAULT '{}'::jsonb,
    primeira_vez_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fonte_id, id_externo)
);

-- Histórico de preço: uma linha por item por execução (só itens com preço)
CREATE TABLE historico_precos (
    item_id          BIGINT NOT NULL REFERENCES itens(id) ON DELETE CASCADE,
    execucao_id      UUID NOT NULL REFERENCES execucoes(id) ON DELETE CASCADE,
    preco_centavos   INTEGER NOT NULL,
    coletado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (item_id, execucao_id)
);
