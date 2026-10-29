# -*- coding: utf-8 -*-
"""Testes puros do fecho_fable.py (sem chamar `claude`): o Fable 5.1 no maximo julga o RESULTADO no fim
das rodadas; ACEITO = mensagem .441 ao dono; REFAZER = nova rodada, ate 3 julgamentos (ordem do dono,
03/10/2026)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fecho_fable as f  # noqa: E402

P40 = ' '.join(['palavra'] * 40)


def _msg(n=4, palavras=40):
    return '\n\n'.join(' '.join(['palavra'] * palavras) for _ in range(n))


def test_modelo_e_effort_fixos():
    assert f.MODELO == 'claude-fable-5-1'
    assert f.EFFORT == 'max'
    assert f.TETO == 3


def test_veredicto_aceito_com_mensagem():
    texto = 'FECHO: ACEITO\n\nMENSAGEM:\n' + _msg()
    v = f.ler_fecho(texto)
    assert v['decisao'] == 'ACEITO'
    assert len(v['paragrafos']) == 4


def test_veredicto_refazer_com_motivos():
    texto = 'FECHO: REFAZER\n\nMOTIVOS:\n1. o portao X deixa passar Y\n2. falta medir Z\n'
    v = f.ler_fecho(texto)
    assert v['decisao'] == 'REFAZER'
    assert v['motivos'] == ['o portao X deixa passar Y', 'falta medir Z']


def test_sem_linha_fecho_e_indefinido():
    assert f.ler_fecho('acho que esta bom')['decisao'] == 'INDEFINIDO'


def test_mensagem_441_valida():
    assert f.problemas_441(f.ler_fecho('FECHO: ACEITO\nMENSAGEM:\n' + _msg())['paragrafos']) == []


def test_mensagem_441_tolerancia_10_por_cento():
    assert f.problemas_441([' '.join(['p'] * 36)] * 4) == []
    assert f.problemas_441([' '.join(['p'] * 44)] * 4) == []
    assert f.problemas_441([' '.join(['p'] * 35)] + [P40] * 3) != []
    assert f.problemas_441([' '.join(['p'] * 45)] + [P40] * 3) != []


def test_mensagem_441_exige_quatro_paragrafos():
    assert f.problemas_441([P40] * 3) != []
    assert f.problemas_441([P40] * 5) != []


def test_mensagem_441_sem_custo():
    com_custo = [P40[:-8] + ' USD 0,50'] + [P40] * 3
    assert any('custo' in p for p in f.problemas_441(com_custo))


def test_aceito_com_mensagem_torta_vira_indefinido():
    v = f.decidir(f.ler_fecho('FECHO: ACEITO\nMENSAGEM:\n' + _msg(n=3)))
    assert v == 'INDEFINIDO'


def test_refazer_sem_motivo_vira_indefinido():
    assert f.decidir(f.ler_fecho('FECHO: REFAZER\nMOTIVOS:\n')) == 'INDEFINIDO'


def test_contador_e_teto():
    with tempfile.TemporaryDirectory() as d:
        assert f.proxima(d) == 1
        os.makedirs(os.path.join(d, 'historico'))
        for n in (1, 2, 3):
            open(os.path.join(d, 'historico', 'fecho.r%d.md' % n), 'w').close()
        assert f.proxima(d) == 4
        assert f.estourou(d)


def test_prompt_cita_regras():
    p = f.prompt(2)
    assert 'FECHO: ACEITO' in p and 'FECHO: REFAZER' in p
    assert '40 palavras' in p and 'quatro' in p.lower()
    assert 'custo' in p.lower()
    assert '2 de 3' in p


def test_argumentos_usam_fable_no_maximo():
    a = f.argumentos('claude.exe')
    assert a[a.index('--model') + 1] == 'claude-fable-5-1'
    assert a[a.index('--effort') + 1] == 'max'
