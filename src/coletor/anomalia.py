"""Regra que decide se uma execução foi boa, suspeita ou falhou.

O robô pode "dar certo" e mesmo assim estar errado: o site mudou o HTML e a coleta
trouxe 3 itens em vez de 1.000. Sem esta regra, ninguém percebe.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

from coletor.modelos import Status


@dataclass(frozen=True)
class Avaliacao:
    status: Status
    motivo: str | None = None


def avaliar_volume(
    itens_validos: int,
    historico: Sequence[int],
    *,
    itens_invalidos: int = 0,
    limiar: float = 0.5,
    minimo_historico: int = 3,
    max_proporcao_invalidos: float = 0.1,
) -> Avaliacao:
    """Compara a coleta de hoje com a média das últimas execuções bem-sucedidas."""
    if itens_validos == 0:
        return Avaliacao("falha", "nenhum item válido coletado")

    total = itens_validos + itens_invalidos
    if itens_invalidos / total > max_proporcao_invalidos:
        return Avaliacao(
            "parcial",
            f"{itens_invalidos} de {total} itens inválidos "
            f"(acima de {max_proporcao_invalidos:.0%}): o HTML do site pode ter mudado",
        )

    # Sem histórico suficiente não dá para comparar: aceita e vai formando a base
    if len(historico) < minimo_historico:
        return Avaliacao("sucesso")

    media = mean(historico)
    if itens_validos < limiar * media:
        return Avaliacao(
            "parcial",
            f"coletou {itens_validos} itens, abaixo de {limiar:.0%} da média recente ({media:.0f})",
        )
    return Avaliacao("sucesso")
