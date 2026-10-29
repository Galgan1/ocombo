# -*- coding: utf-8 -*-
"""O Jev escolhe o modelo e a forca de cada tarefa (ordem do dono, 04/10/2026: "Insira isto em ocombo o jev escolhe
o modelo e a forca"). As travas da casa continuam por cima: lote nunca no topo, conferente de outro tier, F1 compra
tempo, juiz de tier diferente da sessao. Sem Jev = regra fixa com rotulo. Testes com transporte duble (sem rede)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import jev_escolha  # noqa: E402
import sommelier  # noqa: E402


def duble(tier_probs, effort_probs, status=200):
    def transporte(corpo_bytes):
        corpo = json.loads(corpo_bytes.decode("utf-8"))
        assert set(corpo["questions"]) == {"tier", "effort"}
        dados = {"id": "t1", "model": "typesafe/jev-1.13",
                 "answers": {"tier": {"probabilities": tier_probs},
                             "effort": {"probabilities": {str(k): v for k, v in effort_probs.items()}, "score": 0}}}
        return 0, "HTTP %d em 300 ms\n%s" % (status, json.dumps(dados)), ""
    return transporte


def test_jev_escolhe_tier_e_effort():
    j = jev_escolha.perguntar("redacao", "capitulo de livro", 1, duble({"opus": 0.7, "sonnet": 0.3}, {3: 0.8, 2: 0.2}))
    assert j["tier"] == "opus" and j["effort"] == "xhigh" and j["p_tier"] == 0.7


def test_sommelier_usa_o_jev():
    e = sommelier.escolher("redacao", 1, jev={"tier": "opus", "effort": "high", "p_tier": 0.7, "p_effort": 0.6})
    assert e["alias"] == "opus" and e["effort"] == "high" and "Jev" in e["motivo"]


def test_lote_no_topo_continua_proibido_mesmo_se_o_jev_pedir():
    e = sommelier.escolher("transcricao", 44, jev={"tier": "fable", "effort": "max", "p_tier": 0.9, "p_effort": 0.9})
    assert e["alias"] != sommelier.TOPO


def test_conferente_nunca_no_tier_do_autor_mesmo_se_o_jev_pedir():
    e = sommelier.escolher("conferencia", 1, autor="opus", jev={"tier": "opus", "effort": "high", "p_tier": 0.8, "p_effort": 0.8})
    assert e["alias"] != "opus"


def test_f1_continua_comprando_tempo():
    e = sommelier.escolher("pesquisa", 1, modo="f1", jev={"tier": "sonnet", "effort": "max", "p_tier": 0.8, "p_effort": 0.8})
    assert e["effort"] == "low"


def test_juiz_de_tier_diferente_da_sessao():
    e = sommelier.escolher("julgamento", 1, sessao="opus", jev={"tier": "opus", "effort": "high", "p_tier": 0.8, "p_effort": 0.8})
    assert e["alias"] != "opus"


def test_sem_jev_cai_na_regra_fixa_com_rotulo():
    falha = lambda corpo: (255, "", "ssh: timeout")  # noqa: E731
    with pytest.raises(jev_escolha.SemJev):
        jev_escolha.perguntar("redacao", "x", 1, falha)
    p = sommelier.planejar("redacao:2", jev_transporte=falha)
    assert p[0]["alias"] == "sonnet" and "regra fixa" in p[0]["motivo"]


def test_planejar_pergunta_ao_jev_por_classe():
    p = sommelier.planejar("varredura:3,sintese:1", sessao="opus",
                           jev_transporte=duble({"sonnet": 0.6, "haiku": 0.4}, {1: 0.9}))
    assert all("Jev" in e["motivo"] for e in p) and p[0]["alias"] == "sonnet"


def test_resposta_sem_probabilidade_e_sem_jev():
    ruim = lambda corpo: (0, 'HTTP 200 em 1 ms\n{"answers": {}}', "")  # noqa: E731
    with pytest.raises(jev_escolha.SemJev):
        jev_escolha.perguntar("redacao", "x", 1, ruim)
