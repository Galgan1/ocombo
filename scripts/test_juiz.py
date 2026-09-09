# -*- coding: utf-8 -*-
"""Testes puros de juiz.py (nunca chamam `claude`)."""
import os
import shutil
import tempfile
import unittest

import juiz


class TestDelta(unittest.TestCase):
    def test_delta_lista_so_o_que_mudou(self):
        d = juiz.delta('a\nb\nc\n', 'a\nB\nc\nd\n', 'r1', 'r2')
        self.assertIn('-b', d)
        self.assertIn('+B', d)
        self.assertIn('+d', d)
        self.assertIn('--- r1', d)

    def test_delta_vazio_quando_igual(self):
        self.assertEqual(juiz.delta('x\n', 'x\n', 'r1', 'r2'), '')


class TestUsage(unittest.TestCase):
    def test_linha_custo_com_campos(self):
        resp = {'total_cost_usd': 0.0123, 'duration_ms': 4500, 'num_turns': 3,
                'usage': {'input_tokens': 120, 'output_tokens': 800,
                          'cache_read_input_tokens': 9000, 'cache_creation_input_tokens': 300}}
        c = juiz.custo(resp, rodada=2, modelo='claude-sonnet-5')
        self.assertEqual(c['rodada'], 2)
        self.assertEqual(c['input'], 120)
        self.assertEqual(c['cache_read'], 9000)
        self.assertAlmostEqual(c['usd'], 0.0123)
        self.assertEqual(c['segundos'], 4.5)
        linha = juiz.linha_custo(c)
        self.assertIn('r2', linha)
        self.assertIn('claude-sonnet-5', linha)
        self.assertIn('0.0123', linha)

    def test_sem_usage_nao_chuta(self):
        c = juiz.custo({'result': 'texto'}, rodada=1, modelo='m')
        self.assertIsNone(c['usd'])
        self.assertIn('sem usage', juiz.linha_custo(c))


class TestVeredicto(unittest.TestCase):
    def test_canonico(self):
        self.assertEqual(juiz.veredicto('...\nVEREDICTO: APROVADO\n'), 'APROVADO')
        self.assertEqual(juiz.veredicto('VEREDICTO: AJUSTE'), 'AJUSTE')
        self.assertEqual(juiz.veredicto('NAO APROVADO'), 'AJUSTE')
        self.assertEqual(juiz.veredicto(''), 'INDEFINIDO')


class TestPrompt(unittest.TestCase):
    def test_rodada1_le_tudo(self):
        p = juiz.prompt(rodada=1, fails=[], tem_delta=False)
        self.assertIn('solucao.txt', p)
        self.assertNotIn('delta.patch', p)
        self.assertIn('VEREDICTO: APROVADO', p)

    def test_rodada_n_julga_so_fails_e_regressao(self):
        p = juiz.prompt(rodada=3, fails=['C2', 'C5'], tem_delta=True)
        self.assertIn('delta.patch', p)
        self.assertIn('C2', p)
        self.assertIn('C5', p)
        self.assertIn('regress', p.lower())

    def test_extrai_fails_do_veredicto(self):
        v = '- C1: PASS — ok\n- C2: FAIL — faltou X\n* C5 — FAIL: y\nVEREDICTO: AJUSTE\n'
        self.assertEqual(juiz.fails_de(v), ['C2', 'C5'])

    def test_linhas_canonicas_mandam(self):
        v = ('- C2a/C2b — nenhum FAIL de URL; PASS\n'   # prosa que enganaria a heuristica
             'CRITERIO C2a: PASS\nCRITERIO C7: FAIL\nCRITERIO C11: N/A\nVEREDICTO: AJUSTE\n')
        self.assertEqual(juiz.fails_de(v), ['C7'])
        self.assertEqual(juiz.rotulos_canonicos(v), {'C2a': 'PASS', 'C7': 'FAIL', 'C11': 'N/A'})
        self.assertIn('CRITERIO <id>: PASS', juiz.prompt(1, [], False))

    def test_fail_entre_aspas_nao_conta(self):
        v = ('- **C3** — sem "FAIL sem segredo"/"FAIL LF"; `file_eol.txt` sem CRLF. PASS\n'
             '- **Achado 1 — C9**: `grep FAIL` nao achou; FAIL — faltou declarar\n'
             '- C6.3 — PASS\n')
        self.assertEqual(juiz.fails_de(v), ['C9'])


class TestSnapshot(unittest.TestCase):
    def test_snapshot_numera_rodadas_e_gera_delta(self):
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, 'solucao.txt'), 'w', encoding='utf-8', newline='\n') as f:
                f.write('v1\n')
            self.assertEqual(juiz.snapshot(d), 1)
            with open(os.path.join(d, 'solucao.txt'), 'w', encoding='utf-8', newline='\n') as f:
                f.write('v2\n')
            self.assertEqual(juiz.snapshot(d), 2)
            self.assertTrue(os.path.exists(os.path.join(d, 'historico', 'solucao.r1.txt')))
            self.assertIn('-v1', juiz.delta_da_rodada(d, 2))
            self.assertEqual(juiz.delta_da_rodada(d, 1), '')
        finally:
            shutil.rmtree(d)


class TestCarimbo(unittest.TestCase):
    """v6: o APROVADO grava o sha256 do solucao.txt; mudou o arquivo depois, o carimbo CADUCOU."""
    def test_carimbo_grava_confere_e_caduca(self):
        d = tempfile.mkdtemp()
        try:
            sol = os.path.join(d, 'solucao.txt')
            with open(sol, 'w', encoding='utf-8', newline='\n') as f:
                f.write('v1\n')
            self.assertEqual(juiz.carimbo(d)[0], None)          # nunca aprovado
            juiz.gravar_carimbo(d)
            self.assertTrue(os.path.exists(os.path.join(d, 'aprovado.sha256')))
            self.assertEqual(juiz.carimbo(d)[0], 'APROVADO')
            with open(sol, 'w', encoding='utf-8', newline='\n') as f:
                f.write('v1 mexido\n')
            estado, atual, gravado = juiz.carimbo(d)
            self.assertEqual(estado, 'CADUCOU')
            self.assertNotEqual(atual, gravado)
            juiz.apagar_carimbo(d)
            self.assertEqual(juiz.carimbo(d)[0], None)
        finally:
            shutil.rmtree(d)


class TestConformidade(unittest.TestCase):
    """v6: rodada N julga FAIL + N/A (o que o juiz pulou por parar na conformidade ou por ENTREGA ausente)."""
    def test_pendentes_inclui_na(self):
        v = 'CRITERIO C0: FAIL\nCRITERIO C1: PASS\nCRITERIO C5: N/A\nVEREDICTO: AJUSTE\n'
        self.assertEqual(juiz.fails_de(v), ['C0'])
        self.assertEqual(juiz.pendentes_de(v), ['C0', 'C5'])

    def test_prompt_manda_parar_na_conformidade(self):
        p1 = juiz.prompt(1, [], False)
        self.assertIn('CONFORMIDADE', p1)
        self.assertIn('N/A', p1)
        p3 = juiz.prompt(3, ['C0', 'C5'], True)
        self.assertIn('C5', p3)
        self.assertIn('N/A', p3)

    def test_prompt_caveman_por_padrao_e_desligavel(self):
        # v8: a critica sai em caveman full; as linhas que a maquina le nao mudam; OCOMBO_CAVEMAN=off desliga
        p = juiz.prompt(1, [], False, caveman='full')
        self.assertIn('caveman full', p)
        self.assertIn('NUNCA cortar nao/nunca/so/exceto', p)
        self.assertIn('`CRITERIO <id>: PASS`', p)
        self.assertIn('VEREDICTO: APROVADO', p)
        self.assertNotIn('caveman', juiz.prompt(1, [], False, caveman='off'))
        self.assertIn('caveman ultra', juiz.prompt(2, ['C1'], True, caveman='ultra'))
        self.assertEqual(juiz.nivel_caveman('OFF'), 'off')
        self.assertEqual(juiz.nivel_caveman('qualquer-coisa'), 'full')
        self.assertEqual(juiz.nivel_caveman('lite'), 'lite')
        self.assertEqual(juiz.bloco_caveman('off'), '')


class TestComandoProva(unittest.TestCase):
    def test_windows_usa_bat_e_posix_usa_sh(self):
        d = tempfile.mkdtemp()
        try:
            self.assertIsNone(juiz.comando_prova(d, nt=True))
            self.assertIsNone(juiz.comando_prova(d, nt=False))
            open(os.path.join(d, 'prova.bat'), 'w').write('exit /b 0')
            open(os.path.join(d, 'prova.sh'), 'w').write('exit 0')
            self.assertEqual(juiz.comando_prova(d, nt=True)[:2], ['cmd', '/c'])
            self.assertEqual(juiz.comando_prova(d, nt=False)[0], 'sh')
            os.remove(os.path.join(d, 'prova.sh'))
            self.assertIsNone(juiz.comando_prova(d, nt=False))  # so .bat num POSIX = sem portao, nao erro
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
