import json
import logging

from coletor.logs import FormatadorJson


def _registro(**extra: object) -> logging.LogRecord:
    registro = logging.makeLogRecord(
        {"name": "teste", "levelname": "INFO", "msg": "coleta %s", "args": ("ok",)}
    )
    for chave, valor in extra.items():
        setattr(registro, chave, valor)
    return registro


def test_formata_como_json_com_mensagem_interpolada():
    saida = json.loads(FormatadorJson().format(_registro()))
    assert saida["msg"] == "coleta ok"
    assert saida["nivel"] == "INFO"
    assert "ts" in saida


def test_inclui_campos_extras():
    saida = json.loads(FormatadorJson().format(_registro(execucao_id="abc", fonte="livros")))
    assert saida["execucao_id"] == "abc"
    assert saida["fonte"] == "livros"
