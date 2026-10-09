# Imagem oficial do Playwright: já vem com Chromium e as dependências do sistema
FROM mcr.microsoft.com/playwright/python:v1.56.0-noble

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
# Dependências primeiro: camada fica em cache enquanto só o código muda
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
COPY README.md ./
RUN uv sync --locked --no-dev

# Usuário sem privilégio de root
RUN useradd --create-home coletor
USER coletor

CMD ["coletor", "executar", "--todas"]
