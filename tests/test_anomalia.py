from coletor.anomalia import avaliar_volume


def test_zero_itens_e_falha():
    assert avaliar_volume(0, [1000, 1000, 1000]).status == "falha"


def test_sem_historico_suficiente_aceita():
    assert avaliar_volume(5, [1000, 1000]).status == "sucesso"


def test_volume_normal_e_sucesso():
    assert avaliar_volume(980, [1000, 1000, 1000]).status == "sucesso"


def test_queda_brusca_vira_parcial():
    avaliacao = avaliar_volume(20, [1000, 1000, 1000])
    assert avaliacao.status == "parcial"
    assert avaliacao.motivo is not None and "média recente (1000)" in avaliacao.motivo


def test_exatamente_no_limiar_ainda_e_sucesso():
    assert avaliar_volume(500, [1000, 1000, 1000], limiar=0.5).status == "sucesso"


def test_muitos_invalidos_vira_parcial_mesmo_sem_historico():
    avaliacao = avaliar_volume(80, [], itens_invalidos=20)
    assert avaliacao.status == "parcial"
    assert "inválidos" in (avaliacao.motivo or "")


def test_poucos_invalidos_e_tolerado():
    assert avaliar_volume(995, [1000, 1000, 1000], itens_invalidos=5).status == "sucesso"
