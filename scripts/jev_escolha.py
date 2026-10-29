# -*- coding: utf-8 -*-
"""O JEV ESCOLHE O MODELO E A FORCA de cada tarefa do combo (ordem do dono, 04/10/2026: "Insira isto em ocombo o jev
escolhe o modelo e a forca").

Uma chamada ao Jev por classe de tarefa (pela ponte da skill jev: mascara + `ssh vps jev raw`), com duas perguntas:
  tier   (choice): haiku | sonnet | opus | fable
  effort (score) : low | medium | high | xhigh | max
O sommelier aplica a escolha e, POR CIMA, as travas que o dono ja fechou (R2 lote nunca no topo, R3 conferente de
outro tier, R4 F1 compra tempo, juiz de tier diferente da sessao). Sem Jev (rede, cota, resposta torta) = SemJev e o
sommelier volta a regra fixa, com "regra fixa (sem Jev: motivo)" no motivo — nunca um numero inventado.
Desligar: OCOMBO_JEV=off."""
import json
import os
import sys

TIERS = ("haiku", "sonnet", "opus", "fable")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DESCRICAO_TIER = {
    "haiku": "Haiku: rapido e barato; tarefa mecanica (listar, classificar, ler log)",
    "sonnet": "Sonnet: equilibrado; redacao, pesquisa, transcricao, conferencia comum",
    "opus": "Opus: raciocinio forte; codigo dificil, decisao, revisao critica",
    "fable": "Fable: o mais capaz e o mais caro; so o que pede o maximo de julgamento",
}
DESCRICAO_EFFORT = [
    "low: quase nenhum raciocinio",
    "medium: raciocinio normal",
    "high: pensar com cuidado",
    "xhigh: pensar muito, varios passos",
    "max: o maximo de raciocinio",
]


class SemJev(Exception):
    """Qualquer coisa que impede uma escolha honesta do Jev."""


def _jev():
    for d in (os.environ.get("METAJEV_JEV_DIR"), os.path.join(os.path.dirname(__file__), "..", "..", "jev", "scripts"),
              os.path.join(os.path.expanduser("~"), ".claude", "skills", "jev", "scripts")):
        if d and os.path.exists(os.path.join(d, "jev_consulta.py")):
            if d not in sys.path:
                sys.path.insert(0, d)
            import jev_consulta
            return jev_consulta
    return None


def montar_corpo(classe, descricao, agentes):
    j = _jev()
    mascarar = j.mascarar if j else (lambda t: t)
    estado = mascarar("Tarefa de um agente de IA. Classe: %s. Quantos agentes iguais: %d. Descricao: %s"
                      % (classe, agentes, (descricao or "").strip()))[:4000]
    return {"model": j.MODELO if j else "typesafe/jev-1.13", "state": estado, "questions": {
        "tier": {"type": "choice", "criteria": dict(DESCRICAO_TIER),
                 "instructions": "Qual modelo de IA deve fazer esta tarefa, pesando qualidade e preco?"},
        "effort": {"type": "score", "criteria": list(DESCRICAO_EFFORT),
                   "instructions": "Quanto esforco de raciocinio esta tarefa pede do modelo?"}}}


def ler(codigo, saida, erro):
    import re
    m = re.match(r"\s*HTTP (\d+) em (\d+) ms\s*\n(.*)", saida or "", re.S)
    if not m:
        linhas = (erro or saida or "saida vazia").strip().splitlines()
        raise SemJev("bancada nao respondeu (exit %s): %s" % (codigo, linhas[-1] if linhas else "saida vazia"))
    if int(m.group(1)) != 200:
        raise SemJev("HTTP %s" % m.group(1))
    try:
        r = (json.loads(m.group(3)) or {}).get("answers") or {}
    except ValueError:
        raise SemJev("resposta que nao e JSON")
    pt = (r.get("tier") or {}).get("probabilities")
    pe = (r.get("effort") or {}).get("probabilities")
    if not isinstance(pt, dict) or not pt or not set(pt) <= set(TIERS) or not isinstance(pe, dict) or not pe:
        raise SemJev("lote incompleto: tier ou effort sem probabilidade")
    try:
        pe = {int(k): float(v) for k, v in pe.items()}
    except (TypeError, ValueError):
        raise SemJev("effort com probabilidade invalida")
    if not all(0 <= k < len(EFFORTS) for k in pe):
        raise SemJev("effort fora da escala")
    tier = max(pt, key=lambda k: pt[k])
    nivel = max(pe, key=lambda k: pe[k])
    return {"tier": tier, "effort": EFFORTS[nivel], "p_tier": float(pt[tier]), "p_effort": float(pe[nivel])}


def perguntar(classe, descricao, agentes=1, transporte=None):
    """{'tier', 'effort', 'p_tier', 'p_effort'} escolhidos pelo Jev; SemJev se nao houver resposta honesta."""
    if transporte is None:
        j = _jev()
        if j is None:
            raise SemJev("skill jev nao encontrada")
        transporte = j.transporte_padrao
    corpo = json.dumps(montar_corpo(classe, descricao, agentes), ensure_ascii=False).encode("utf-8")
    return ler(*transporte(corpo))


def ligado():
    return os.environ.get("OCOMBO_JEV", "on").lower() not in ("off", "0", "nao", "não")
