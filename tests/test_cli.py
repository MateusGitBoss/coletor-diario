from typer.testing import CliRunner

from coletor.cli import app


def test_executar_sem_fonte_explica_o_uso():
    resultado = CliRunner().invoke(app, ["executar"])
    assert resultado.exit_code == 2
    assert "livros" in resultado.output


def test_fonte_desconhecida_e_recusada():
    resultado = CliRunner().invoke(app, ["executar", "--fonte", "nao-existe"])
    assert resultado.exit_code == 2
