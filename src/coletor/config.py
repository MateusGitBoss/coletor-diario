"""Configuração lida de variáveis de ambiente (ou do arquivo .env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/coletor"
    discord_webhook_url: str = ""
    limiar_anomalia: float = 0.5
    janela_anomalia: int = 7
    http_timeout_segundos: float = 20.0
    pausa_entre_paginas_segundos: float = 0.3
    artefatos_dir: str = "artefatos"
    cors_origens: str = "http://localhost:5173"
    nivel_log: str = "INFO"

    @property
    def lista_cors_origens(self) -> list[str]:
        return [o.strip() for o in self.cors_origens.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
