# -*- coding: utf-8 -*-
"""Testes puros de ledger.py (arquivo temporario, sem tocar ~/.claude). Rodar: python -m unittest -q test_ledger"""
import os
import tempfile
import unittest

import ledger


class TestLedger(unittest.TestCase):
    def setUp(self):
        fd, self.p = tempfile.mkstemp(suffix='.jsonl')
        os.close(fd)
        os.remove(self.p)

    def tearDown(self):
        if os.path.exists(self.p):
            os.remove(self.p)

    def test_gravar_e_carregar(self):
        ledger.gravar({'instancia': 'x', 'tipo': 'veredicto', 'rodada': 'r1', 'veredicto': 'APROVADO', 'usd': '0.5',
                       'ts': '2026-09-06T10:00:00'}, self.p)
        itens = ledger.carregar(self.p)
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]['veredicto'], 'APROVADO')

    def test_pendentes_fecha_com_sim_da_mesma_instancia(self):
        itens = [
            {'instancia': 'a', 'tipo': 'escalada', 'regua': 'producao', 'texto': 'deploy', 'ts': '2026-09-06T10:00:00'},
            {'instancia': 'b', 'tipo': 'escalada', 'regua': 'dinheiro', 'texto': 'pagar', 'ts': '2026-09-06T10:01:00'},
            {'instancia': 'a', 'tipo': 'sim', 'texto': 'pode subir', 'ts': '2026-09-06T10:02:00'},
        ]
        abertas = ledger.pendentes(itens)
        self.assertEqual([e['instancia'] for e in abertas], ['b'])
        self.assertEqual(ledger.pendentes(itens, 'a'), [])

    def test_sim_com_fecha_fecha_a_escalada_certa_nao_a_ultima(self):
        # 15/09/2026: o sim LIFO fechou escalada errada (incidente de 08/09/2026)
        itens = [
            {'instancia': 'a', 'tipo': 'escalada', 'regua': 'decisao', 'texto': 'E1 liberar o portao', 'ts': '2026-09-15T10:00:00'},
            {'instancia': 'a', 'tipo': 'escalada', 'regua': 'decisao', 'texto': 'E2 login manual', 'ts': '2026-09-15T10:00:01'},
            {'instancia': 'a', 'tipo': 'escalada', 'regua': 'producao', 'texto': 'E3 criar a tarefa', 'ts': '2026-09-15T10:00:02'},
            {'instancia': 'a', 'tipo': 'sim', 'texto': 'pode acessar', 'fecha': 'E1', 'ts': '2026-09-15T12:00:00'},
        ]
        self.assertEqual([e['texto'] for e in ledger.pendentes(itens, 'a')], ['E2 login manual', 'E3 criar a tarefa'])

    def test_sim_com_fecha_sem_par_nao_fecha_nada(self):
        itens = [
            {'instancia': 'a', 'tipo': 'escalada', 'regua': 'producao', 'texto': 'E3 criar a tarefa', 'ts': '2026-09-15T10:00:02'},
            {'instancia': 'a', 'tipo': 'sim', 'texto': 'ok', 'fecha': 'E9', 'ts': '2026-09-15T12:00:00'},
        ]
        self.assertEqual(len(ledger.pendentes(itens, 'a')), 1)

    def test_sim_sem_fecha_continua_lifo(self):
        itens = [
            {'instancia': 'a', 'tipo': 'escalada', 'regua': 'decisao', 'texto': 'E1', 'ts': '2026-09-15T10:00:00'},
            {'instancia': 'a', 'tipo': 'escalada', 'regua': 'producao', 'texto': 'E3', 'ts': '2026-09-15T10:00:02'},
            {'instancia': 'a', 'tipo': 'sim', 'texto': 'ok', 'ts': '2026-09-15T12:00:00'},
        ]
        self.assertEqual([e['texto'] for e in ledger.pendentes(itens, 'a')], ['E1'])

    def test_sim_sem_escalada_nao_quebra(self):
        self.assertEqual(ledger.pendentes([{'instancia': 'a', 'tipo': 'sim', 'texto': 'ok'}]), [])

    def test_resumo_do_dia(self):
        itens = [
            {'instancia': 'bot', 'tipo': 'veredicto', 'rodada': 'r1', 'veredicto': 'AJUSTE', 'usd': '0.5', 'ts': '2026-09-06T10:00:00'},
            {'instancia': 'bot', 'tipo': 'veredicto', 'rodada': 'r2', 'veredicto': 'APROVADO', 'usd': '0.25', 'ts': '2026-09-06T11:00:00'},
            {'instancia': 'bot', 'tipo': 'escalada', 'regua': 'producao', 'texto': 'subir na VPS', 'ts': '2026-09-06T11:05:00'},
            {'instancia': 'outro', 'tipo': 'veredicto', 'rodada': 'r1', 'veredicto': 'APROVADO', 'usd': '1', 'ts': '2026-09-05T11:00:00'},
        ]
        linhas = ledger.resumo(itens, '2026-09-06')
        texto = '\n'.join(linhas)
        self.assertIn('ciclos 1  rodadas 2  aprovadas 1', texto)
        self.assertIn('USD total 0.75', texto)
        self.assertIn('ESPEROU VOCE [producao] subir na VPS', texto)
        self.assertIn('escaladas abertas: 1', texto)
        self.assertNotIn('outro', texto)
        self.assertTrue(all(len(l) <= ledger.LARGURA for l in linhas), 'cupom de 40 colunas')

    def test_ilegivel_nao_derruba(self):
        with open(self.p, 'w', encoding='utf-8') as f:
            f.write('{"instancia": "a", "tipo": "sim", "texto": "ok"}\nnao e json\n')
        itens = ledger.carregar(self.p)
        self.assertEqual(itens[1]['tipo'], 'ilegivel')


if __name__ == '__main__':
    unittest.main()
