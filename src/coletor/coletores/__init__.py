"""Registro das fontes disponíveis."""

from coletor.coletores.base import Coletor
from coletor.coletores.citacoes import ColetorCitacoes
from coletor.coletores.livros import ColetorLivros
from coletor.config import Settings


def criar_coletores(settings: Settings) -> dict[str, Coletor]:
    return {
        "livros": ColetorLivros(
            pausa_segundos=settings.pausa_entre_paginas_segundos,
            timeout_segundos=settings.http_timeout_segundos,
        ),
        "citacoes": ColetorCitacoes(artefatos_dir=settings.artefatos_dir),
    }


__all__ = ["Coletor", "ColetorCitacoes", "ColetorLivros", "criar_coletores"]
