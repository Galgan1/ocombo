# -*- coding: utf-8 -*-
"""Testes puros dos MODOS do combo (v9). Nunca chamam `claude` nem tocam a rede.

Rodar: python -m unittest -q test_modos   (o prova.py da skill roda junto com os outros)
"""
import os
import unittest

import juiz
import modos


class Tabela(unittest.TestCase):
    def test_doze_perfis(self):
        """0..10 mais o f1: a escala inteira, sem buraco."""
        self.assertEqual(sorted(k for k in modos.PERFIS if isinstance(k, int)), list(range(11)))
        self.assertIn('f1', modos.PERFIS)
        self.assertEqual(len(modos.PERFIS), 12)

    def test_v16_gemini_fora_do_processo(self):
        """v16 (26/10/2026, o dono: "esqueça gemini. registre isto no processo."): nenhum perfil julga pelo agy/Gemini."""
        for chave, p in modos.PERFIS.items():
            self.assertFalse(p['juiz'].startswith('agy:'), 'perfil %r ainda julga pelo agy' % chave)
            self.assertNotIn('gemini', (p['juiz'] + ' ' + p['resumo']).lower(), 'perfil %r cita o Gemini' % chave)
        self.assertEqual(juiz.MODELO_PADRAO, 'claude-sonnet-5-5')
        self.assertFalse([j for j in modos.JUIZES_PERMITIDOS if j.startswith('agy:')])

    def test_campos_obrigatorios_em_todo_perfil(self):
        for chave, p in modos.PERFIS.items():
            for campo in ('apelido', 'juiz', 'rodadas', 'timeout', 'dupla', 'paralelo',
                          'custo_relativo', 'fast', 'resumo'):
                self.assertIn(campo, p, 'perfil %r sem campo %s' % (chave, campo))

    def test_modo_zero_e_o_combo_de_hoje(self):
        """C1: o padrao nao muda para quem nao escolhe modo."""
        p = modos.PERFIS[0]
        self.assertEqual(p['juiz'], juiz.MODELO_PADRAO)
        self.assertEqual(p['timeout'], juiz.TIMEOUT_PADRAO)
        self.assertEqual(p['rodadas'], 5)
        self.assertEqual(p['dupla'], 'nao')
        self.assertIsNone(p['juiz_effort'])
        self.assertIsNone(p['executor_effort'])
        self.assertFalse(p['fast'])

    def test_escala_monotonica(self):
        """C2: de N para N+1 nada DIMINUI (rodadas e custo declarado)."""
        for n in range(10):
            a, b = modos.PERFIS[n], modos.PERFIS[n + 1]
            self.assertLessEqual(a['rodadas'], b['rodadas'], 'rodadas caem de %d para %d' % (n, n + 1))
            self.assertLess(a['custo_relativo'], b['custo_relativo'], 'custo nao sobe de %d para %d' % (n, n + 1))

    def test_dez_e_o_topo_da_escala(self):
        maior = max(modos.PERFIS[n]['custo_relativo'] for n in range(11))
        self.assertEqual(modos.PERFIS[10]['custo_relativo'], maior)
        # 29/10/2026 (uso enxuto): o topo nao compra effort nem dupla em toda rodada; compra rodadas, pesquisa e fan-out.
        self.assertEqual(modos.PERFIS[10]['dupla'], 'regua')
        self.assertEqual(modos.PERFIS[10]['executor_effort'], 'high')
        self.assertEqual(modos.PERFIS[10]['juiz_effort'], 'medium')
        for chave, p in modos.PERFIS.items():
            self.assertNotEqual(p['dupla'], 'sempre', 'perfil %r ainda liga dupla em toda rodada' % chave)
            if chave != 'f1':
                self.assertLessEqual(p['paralelo'], 4, 'perfil %r acima de 4 agentes por leva' % chave)

    def test_juiz_sempre_cross_model(self):
        """H3: a tabela nunca oferece juiz do tier do executor (Fable/Opus executam)."""
        for chave, p in modos.PERFIS.items():
            self.assertIn(p['juiz'], modos.JUIZES_PERMITIDOS, 'perfil %r com juiz fora da lista' % chave)


class Piso(unittest.TestCase):
    """C3: nenhum modo desliga portao — o que varia e o gasto ACIMA do piso."""

    def test_portoes_iguais_em_todos_os_perfis(self):
        for chave in modos.PERFIS:
            self.assertEqual(modos.portoes(chave), modos.PORTOES, 'perfil %r mexeu no piso' % chave)

    def test_nenhum_perfil_traz_chave_que_apaga_portao(self):
        proibidas = ('sem_prova', 'sem_triagem', 'sem_lint', 'sem_escalada', 'pular_portao', 'sem_carimbo')
        for chave, p in modos.PERFIS.items():
            for k in proibidas:
                self.assertNotIn(k, p, 'perfil %r tenta desligar portao (%s)' % (chave, k))

    def test_piso_cita_as_quatro_travas(self):
        junto = ' '.join(modos.PORTOES).lower()
        for trava in ('prova', 'triagem', 'lint', 'escalada'):
            self.assertIn(trava, junto)


class FormulaUm(unittest.TestCase):
    """C4: F1 e o eixo do TEMPO, nao o topo da escala."""

    def test_f1_corre_menos_rodadas_que_o_opala(self):
        self.assertLess(modos.PERFIS['f1']['rodadas'], modos.PERFIS[10]['rodadas'])

    def test_f1_paraleliza_pelo_menos_como_o_opala(self):
        self.assertGreaterEqual(modos.PERFIS['f1']['paralelo'], modos.PERFIS[10]['paralelo'])

    def test_f1_tem_timeout_curto_e_juiz_rapido(self):
        p = modos.PERFIS['f1']
        self.assertLess(p['timeout'], modos.PERFIS[0]['timeout'])
        self.assertEqual(p['juiz_effort'], 'low')

    def test_f1_nao_liga_fast_sozinho(self):
        self.assertFalse(modos.PERFIS['f1']['fast'])
        self.assertIsNone(modos.PERFIS['f1']['escalada'])

    def test_turbo_liga_fast_e_escala_dinheiro(self):
        """fast mode sai de usage credits: e DINHEIRO, regua v5."""
        t = modos.turbo(modos.PERFIS['f1'])
        self.assertTrue(t['fast'])
        self.assertEqual(t['escalada'], 'dinheiro')
        self.assertFalse(modos.PERFIS['f1']['fast'], 'turbo() nao pode mutar a tabela')

    def test_turbo_recusa_perfil_que_nao_declara_suporte(self):
        """fast mode "is not available on Sonnet, Haiku, or other models": so o F1 declara turbo."""
        with self.assertRaises(ValueError):
            modos.turbo(modos.PERFIS[0])

    def test_stagger_zero_so_no_f1(self):
        amb = modos.ambiente(modos.PERFIS['f1'])
        self.assertEqual(amb.get('CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS'), '0')
        self.assertNotIn('CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS', modos.ambiente(modos.PERFIS[0]))


class Normalizacao(unittest.TestCase):
    def test_numero_texto_e_apelido(self):
        self.assertEqual(modos.normalizar(0), 0)
        self.assertEqual(modos.normalizar('7'), 7)
        self.assertEqual(modos.normalizar(' 10 '), 10)
        self.assertEqual(modos.normalizar('f1'), 'f1')
        self.assertEqual(modos.normalizar('F1'), 'f1')
        self.assertEqual(modos.normalizar('opala'), 10)
        self.assertEqual(modos.normalizar('padrao'), 0)

    def test_invalido_levanta(self):
        for v in ('11', '-1', 'formula', '', 'f2', '3.5'):
            with self.assertRaises(ValueError, msg='aceitou %r' % v):
                modos.normalizar(v)

    def test_perfil_le_o_ambiente(self):
        antes = os.environ.get('OCOMBO_MODO')
        try:
            os.environ.pop('OCOMBO_MODO', None)
            self.assertEqual(modos.perfil()['apelido'], modos.PERFIS[0]['apelido'])
            os.environ['OCOMBO_MODO'] = '9'
            self.assertEqual(modos.perfil()['rodadas'], modos.PERFIS[9]['rodadas'])
            os.environ['OCOMBO_MODO'] = 'lixo'
            with self.assertRaises(ValueError):
                modos.perfil()
        finally:
            os.environ.pop('OCOMBO_MODO', None)
            if antes is not None:
                os.environ['OCOMBO_MODO'] = antes

    def test_linha_do_estado(self):
        linha = modos.linha_estado(modos.PERFIS['f1'])
        self.assertIn('f1', linha.lower())
        self.assertIn('rodadas', linha.lower())

    def test_ambiente_devolve_a_chave_e_volta_por_normalizar(self):
        """Bug pego pelo TDD em 09/09/2026: com o APELIDO, OCOMBO_MODO=conferido nao voltava (modo 1)."""
        for chave, p in modos.PERFIS.items():
            valor = modos.ambiente(p)['OCOMBO_MODO']
            self.assertEqual(modos.normalizar(valor), chave, 'ida e volta quebrou no modo %r' % chave)


class Effort(unittest.TestCase):
    """C5: a CLI 2.1.263 ACEITA valor errado com um aviso e roda assim mesmo (medido 09/09/2026,
    `--effort banana` custou USD 0,47). Quem valida somos nos."""

    def test_lista_fechada(self):
        self.assertEqual(modos.EFFORT_VALIDO, ('low', 'medium', 'high', 'xhigh', 'max'))

    def test_valida_bons(self):
        for v in modos.EFFORT_VALIDO:
            self.assertEqual(modos.validar_effort(v), v)

    def test_reprova_banana_e_ultracode(self):
        for v in ('banana', 'ultracode', 'LOW ', None, ''):
            with self.assertRaises(ValueError, msg='aceitou %r' % v):
                modos.validar_effort(v)

    def test_todo_effort_da_tabela_e_valido(self):
        for chave, p in modos.PERFIS.items():
            if p.get('juiz_effort') is not None:
                self.assertEqual(modos.validar_effort(p['juiz_effort']), p['juiz_effort'])


class LinhaDeComando(unittest.TestCase):
    """C1 e C6: sem modo, a linha do `claude` e a de sempre; com modo, so acrescenta --effort."""

    BASE = ['-p', '--model', 'claude-sonnet-5-5', '--permission-mode', 'acceptEdits',
            '--output-format', 'json', '--no-session-persistence']

    def test_sem_effort_e_a_linha_de_antes(self):
        self.assertEqual(juiz.argumentos_claude('claude-sonnet-5-5', None, executavel='claude'),
                         ['claude'] + self.BASE)

    def test_com_effort_acrescenta_no_fim(self):
        self.assertEqual(juiz.argumentos_claude('claude-sonnet-5-5', 'xhigh', executavel='claude'),
                         ['claude'] + self.BASE + ['--effort', 'xhigh'])

    def test_effort_invalido_nao_vira_argumento(self):
        with self.assertRaises(ValueError):
            juiz.argumentos_claude('claude-sonnet-5-5', 'banana', executavel='claude')

    def test_precedencia_explicito_vence_modo(self):
        p = modos.PERFIS[6]
        self.assertEqual(juiz.resolver_modelo('claude-haiku-4-5-20251001', p), 'claude-haiku-4-5-20251001')
        self.assertEqual(juiz.resolver_modelo(None, p), p['juiz'])
        self.assertEqual(juiz.resolver_timeout(120, p), 120)
        self.assertEqual(juiz.resolver_timeout(None, p), p['timeout'])


class TestDoseEEscada(unittest.TestCase):
    def test_ajustar(self):
        self.assertEqual(modos.ajustar(3, '+'), 4)
        self.assertEqual(modos.ajustar(3, '+2'), 5)
        self.assertEqual(modos.ajustar('opala', '+'), 10)
        self.assertEqual(modos.ajustar(0, '-3'), 0)
        for ruim in ('', '2', '+x', '*'):
            with self.assertRaises(ValueError):
                modos.ajustar(3, ruim)
        with self.assertRaises(ValueError):
            modos.ajustar('f1', '+')

    def test_interpretar_dose_colada(self):
        self.assertEqual(modos.interpretar('3'), 3)
        self.assertEqual(modos.interpretar('3+'), 4)
        self.assertEqual(modos.interpretar('3+2'), 5)
        self.assertEqual(modos.interpretar('7-'), 6)
        self.assertEqual(modos.interpretar('opala+'), 10)
        self.assertEqual(modos.interpretar('formula-1'), 'f1')    # apelido com hifen nao e dose
        self.assertEqual(modos.interpretar(7), 7)
        for ruim in ('f1+', '11', 'x+', '3+banana'):
            with self.assertRaises(ValueError):
                modos.interpretar(ruim)

    def test_linha_estado_com_escada(self):
        p = modos.PERFIS[2]
        self.assertFalse(modos.linha_estado(p).endswith('escada: sim'))
        self.assertTrue(modos.linha_estado(p, escada=True).endswith('| escada: sim'))

    def test_escalar_sobe_so_com_falha_e_tem_teto(self):
        self.assertEqual(modos.escalar(2, 0), 2)
        self.assertEqual(modos.escalar(2, 1), 3)
        self.assertEqual(modos.escalar(2, 9), 5)      # no maximo 3 degraus
        self.assertEqual(modos.escalar(8, 3), 9)      # nunca passa de 9 sozinha
        self.assertEqual(modos.escalar(10, 3), 10)
        self.assertEqual(modos.escalar('f1', 3), 'f1')

    def test_escada_nao_mexe_no_piso(self):
        for k in range(10):
            self.assertEqual(modos.portoes(modos.escalar(k, 2)), modos.PORTOES)

    def test_rodadas_ajuste_conta_so_ajuste(self):
        import tempfile
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'historico'))
        for n, v in ((1, 'AJUSTE'), (2, 'AJUSTE'), (3, 'APROVADO')):
            open(os.path.join(d, 'historico', 'veredicto.r%d.md' % n), 'w', encoding='utf-8').write('VEREDICTO: %s' % v)
        self.assertEqual(juiz._rodadas_ajuste(d), 2)


if __name__ == '__main__':
    unittest.main()
