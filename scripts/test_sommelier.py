# -*- coding: utf-8 -*-
"""Testes puros do SOMMELIER POR TAREFA (v11). Nunca chamam `claude` nem tocam a rede.

Rodar: python -m unittest -q test_sommelier   (o prova.py da skill roda junto com os outros)
"""
import json
import os
import re
import subprocess
import sys
import unittest

import modos
import sommelier

AQUI = os.path.dirname(os.path.abspath(__file__))
MODOS = list(range(11)) + ['f1']


class Tabela(unittest.TestCase):
    def test_classes_sao_lista_fechada(self):
        self.assertEqual(sorted(sommelier.CLASSES),
                         ['codigo', 'conferencia', 'julgamento', 'pesquisa', 'redacao', 'sintese',
                          'transcricao', 'varredura'])

    def test_classe_desconhecida_levanta(self):
        """Classe inventada nao vira "herda a sessao" em silencio: foi assim que nasceu o erro."""
        with self.assertRaises(ValueError):
            sommelier.escolher('banana')

    def test_agentes_tem_de_ser_positivo(self):
        for ruim in (0, -1):
            with self.assertRaises(ValueError):
                sommelier.escolher('varredura', agentes=ruim)

    def test_sessao_desconhecida_levanta(self):
        with self.assertRaises(ValueError):
            sommelier.escolher('codigo', sessao='gpt')

    def test_ids_batem_com_os_juizes_da_casa(self):
        for alias in ('haiku', 'sonnet', 'opus'):
            self.assertIn(sommelier.IDS[alias], modos.JUIZES_PERMITIDOS)
        self.assertEqual(sommelier.TIERS[-1], sommelier.TOPO)

    def test_preco_cresce_com_o_tier(self):
        saidas = [sommelier.PRECO[t][1] for t in sommelier.TIERS]
        self.assertEqual(saidas, sorted(saidas))

    def test_razao_entrada_saida_igual_em_todo_tier(self):
        """Premissa do custo relativo: se a saida e sempre 5x a entrada, a razao entre tiers nao
        depende da mistura input/output. Preco mudou e a premissa caiu? Este teste avisa."""
        razoes = set(sommelier.PRECO[t][1] / sommelier.PRECO[t][0] for t in sommelier.TIERS)
        self.assertEqual(len(razoes), 1)


class Escolha(unittest.TestCase):
    def test_o_caso_que_pariu_a_regra(self):
        """20/09/2026: 44 lotes de transcricao sairam em Fable porque ninguem escolheu."""
        e = sommelier.escolher('transcricao', agentes=44)
        self.assertEqual(e['alias'], 'sonnet')
        self.assertEqual(e['modelo'], 'claude-sonnet-5-5')
        self.assertTrue(e['lote'])

    def test_varredura_e_haiku_low(self):
        e = sommelier.escolher('varredura', agentes=10)
        self.assertEqual((e['alias'], e['effort']), ('haiku', 'low'))

    def test_lote_nunca_no_topo(self):
        """A REGRA: 3+ agentes da mesma classe jamais rodam no tier de topo — em nenhuma classe,
        nenhum modo (o 10 tambem) e nenhuma sessao."""
        for classe in sommelier.CLASSES:
            for modo in MODOS:
                for sessao in sommelier.TIERS:
                    for n in (sommelier.LOTE_MIN, 8, 44, 200):
                        e = sommelier.escolher(classe, agentes=n, modo=modo, sessao=sessao)
                        self.assertNotEqual(e['alias'], sommelier.TOPO,
                                            '%s x%d modo %s sessao %s' % (classe, n, modo, sessao))

    def test_decisao_sozinha_herda_a_sessao(self):
        for classe in ('codigo', 'sintese'):
            self.assertEqual(sommelier.escolher(classe, agentes=1, sessao='fable')['alias'], 'fable')
            self.assertEqual(sommelier.escolher(classe, agentes=2, sessao='opus')['alias'], 'opus')

    def test_decisao_em_lote_desce_para_opus(self):
        e = sommelier.escolher('codigo', agentes=5, sessao='fable')
        self.assertEqual(e['alias'], 'opus')
        self.assertIn('lote', e['motivo'])

    def test_conferente_e_cross_model(self):
        for autor in sommelier.TIERS:
            c = sommelier.conferente_de(autor)
            self.assertNotEqual(c, autor)
            self.assertNotEqual(c, sommelier.TOPO)
        self.assertEqual(sommelier.conferente_de('haiku'), 'sonnet')
        self.assertEqual(sommelier.conferente_de('sonnet'), 'opus')
        self.assertEqual(sommelier.conferente_de('fable'), 'sonnet')   # regra da casa: topo executa, Sonnet julga

    def test_julgamento_obedece_ao_modo(self):
        # v16 (26/10/2026, "esqueça gemini"): o juiz do modo volta a ser o Sonnet 5.5 (tier diferente do executor)
        e0 = sommelier.escolher('julgamento', modo=0)
        self.assertEqual((e0['alias'], e0['modelo'], e0['effort']), ('sonnet', 'claude-sonnet-5-5', None))
        self.assertEqual(sommelier.escolher('julgamento', modo=7)['modelo'], modos.PERFIS[7]['juiz'])
        self.assertIn('modos.py', e0['motivo'])

    def test_effort_sempre_valido(self):
        for classe in sommelier.CLASSES:
            for modo in MODOS:
                ef = sommelier.escolher(classe, agentes=4, modo=modo)['effort']
                if ef is not None:
                    self.assertIn(ef, modos.EFFORT_VALIDO)

    def test_modo_alto_compra_effort_nao_tier(self):
        baixo = sommelier.escolher('conferencia', agentes=44, modo=0, autor='sonnet')
        alto = sommelier.escolher('conferencia', agentes=44, modo=10, autor='sonnet')
        self.assertEqual(baixo['alias'], alto['alias'])
        self.assertEqual((baixo['effort'], alto['effort']), ('high', 'xhigh'))

    def test_f1_derruba_o_effort_do_mecanico(self):
        self.assertEqual(sommelier.escolher('transcricao', agentes=44, modo='f1')['effort'], 'low')


class Plano(unittest.TestCase):
    def test_conferencia_confere_a_classe_anterior(self):
        p = sommelier.planejar('transcricao:44,conferencia:44,sintese:1')
        self.assertEqual([e['alias'] for e in p], ['sonnet', 'opus', 'fable'])

    def test_custo_relativo_do_caso_do_dia(self):
        p = sommelier.planejar('transcricao:44,conferencia:44')
        self.assertAlmostEqual(sommelier.custo_relativo(p), 0.30)

    def test_tudo_no_topo_custa_um(self):
        forcado = [dict(e, alias=sommelier.TOPO) for e in sommelier.planejar('sintese:1,codigo:2')]
        self.assertAlmostEqual(sommelier.custo_relativo(forcado), 1.0)

    def test_usd_so_com_volume_informado(self):
        p = sommelier.planejar('transcricao:44')
        self.assertAlmostEqual(sommelier.usd(p, 1000000, 100000), 44 * (2 + 1.0))

    def test_plano_malformado_levanta(self):
        for ruim in ('', 'transcricao', 'transcricao:x', 'transcricao:44=gpt', ':3'):
            with self.assertRaises(ValueError):
                sommelier.planejar(ruim)

    def test_linha_estado_traz_cada_classe(self):
        linha = sommelier.linha_estado(sommelier.planejar('transcricao:44,conferencia:44'))
        for pedaco in ('Sommelier:', 'transcricao x44 sonnet', 'conferencia x44 opus', '30%'):
            self.assertIn(pedaco, linha)


class Checagem(unittest.TestCase):
    def test_lote_no_topo_e_regua_de_dinheiro(self):
        v, _ = sommelier.checar('transcricao:44=fable')
        self.assertEqual(len(v), 1)
        self.assertIn('DINHEIRO', v[0])

    def test_par_no_topo_passa_com_aviso(self):
        v, avisos = sommelier.checar('transcricao:2=fable')
        self.assertEqual(v, [])
        self.assertTrue(avisos)

    def test_conferente_no_tier_do_autor_reprova(self):
        v, _ = sommelier.checar('transcricao:44,conferencia:44=sonnet')
        self.assertTrue(any('cross-model' in x for x in v))

    def test_plano_da_tabela_passa_limpo(self):
        self.assertEqual(sommelier.checar('varredura:20,transcricao:44,conferencia:44,sintese:1'), ([], []))


class Workflow(unittest.TestCase):
    """04/10/2026: a ferramenta Agent aceita `model` mas NAO `effort`; so o agent() do Workflow aceita effort. No
    ciclo do dia quase todo no rodou sem o esforco escolhido. Regra: classe com effort sai por Workflow agent() com
    model E effort; a ferramenta Agent so com effort padrao (None), declarado no ESTADO (linha Lancamento)."""

    @staticmethod
    def _objeto(trecho):
        return json.loads(re.search(r'const SOMMELIER = (\{.*?\n\})', trecho, re.S).group(1))

    def test_opcoes_trazem_effort_sempre_que_a_classe_tem(self):
        """A trava: em toda classe, modo, sessao e tamanho, effort escolhido = effort no agent() e via Workflow."""
        for classe in sommelier.CLASSES:
            for modo in MODOS:
                for sessao in sommelier.TIERS:
                    for n in (1, sommelier.LOTE_MIN):
                        e = sommelier.escolher(classe, n, modo, sessao)
                        o = sommelier.opcoes_workflow(e)
                        quem = '%s x%d modo %s sessao %s' % (classe, n, modo, sessao)
                        self.assertEqual(o['model'], e['alias'], quem)
                        if e['effort'] is None or e['alias'] == 'haiku':     # Haiku 4.5 nao aceita effort
                            self.assertEqual(o, {'model': e['alias']}, quem)
                            self.assertEqual(sommelier.lancar_por(e), 'agent', quem)
                        else:
                            self.assertEqual(o['effort'], e['effort'], quem)
                            self.assertEqual(sommelier.lancar_por(e), 'workflow', quem)

    def test_o_effort_do_jev_vai_no_agent_do_workflow(self):
        e = sommelier.escolher('codigo', 1, sessao='opus',
                               jev={'tier': 'opus', 'effort': 'xhigh', 'p_tier': 0.7, 'p_effort': 0.8})
        self.assertEqual(sommelier.opcoes_workflow(e), {'model': 'opus', 'effort': 'xhigh'})
        self.assertEqual(sommelier.lancar_por(e), 'workflow')

    def test_haiku_vai_sem_effort(self):
        """04/10/2026 (revisor): o catalogo da metajev diz que Haiku 4.5 nao aceita effort (a API da erro). A CLI
        `claude -p --model claude-haiku-4-5-20251001 --effort low` saiu 0 (medido), mas o efeito e nulo: omitir."""
        jev = {'tier': 'haiku', 'effort': 'medium', 'p_tier': 0.7, 'p_effort': 0.7}
        for e in (sommelier.escolher('varredura', 5), sommelier.escolher('redacao', 1, jev=jev)):
            self.assertEqual(sommelier.opcoes_workflow(e), {'model': 'haiku'})
            self.assertEqual(sommelier.lancar_por(e), 'agent')

    def test_trecho_e_objeto_js_que_o_json_le(self):
        trecho = sommelier.trecho_workflow(sommelier.planejar('transcricao:44,conferencia:44,codigo:1', sessao='opus'))
        obj = self._objeto(trecho)
        self.assertEqual(obj['transcricao'], {'model': 'sonnet', 'effort': 'medium'})
        self.assertEqual(obj['conferencia'], {'model': 'opus', 'effort': 'high'})
        self.assertEqual(obj['codigo'], {'model': 'opus'})          # effort padrao: so model
        self.assertIn('agent(prompt, {...SOMMELIER[', trecho)

    def test_classe_repetida_nao_some(self):
        obj = self._objeto(sommelier.trecho_workflow(sommelier.planejar('redacao:3,conferencia:3,redacao:1')))
        self.assertEqual(list(obj), ['redacao', 'conferencia', 'redacao_2'])

    def test_linha_lancamento_declara_quem_vai_pela_ferramenta_agent(self):
        linha = sommelier.linha_lancamento(sommelier.planejar('transcricao:44,codigo:1', sessao='opus'))
        self.assertEqual(linha, 'Lancamento: Workflow agent() model+effort: transcricao | '
                                'ferramenta Agent (effort padrao): codigo')
        self.assertNotIn('ferramenta Agent', sommelier.linha_lancamento(sommelier.planejar('transcricao:44')))

    def _cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(AQUI, 'sommelier.py')] + list(args),
                              capture_output=True, text=True, encoding='utf-8', errors='replace',
                              env=dict(os.environ, OCOMBO_JEV='off'))     # sem rede: regra fixa

    def test_cli_plano_workflow(self):
        r = self._cli('--plano', 'transcricao:44,conferencia:44', '--workflow')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for pedaco in ('Sommelier:', 'Lancamento: Workflow agent() model+effort: transcricao, conferencia',
                       '"transcricao": {"model": "sonnet", "effort": "medium"}'):
            self.assertIn(pedaco, r.stdout)

    def test_cli_tarefa_workflow(self):
        r = self._cli('--tarefa', 'varredura', '--agentes', '5', '--workflow')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('"varredura": {"model": "haiku"}', r.stdout)                 # Haiku 4.5 sem effort
        self.assertIn('ferramenta Agent (effort padrao): varredura', r.stdout)

    def test_sem_workflow_a_saida_antiga_fica(self):
        r = self._cli('--plano', 'transcricao:44')
        self.assertEqual(r.returncode, 0)
        self.assertNotIn('const SOMMELIER', r.stdout)


class Cli(unittest.TestCase):
    def _rodar(self, *args):
        return subprocess.run([sys.executable, os.path.join(AQUI, 'sommelier.py')] + list(args),
                              capture_output=True, text=True, encoding='utf-8', errors='replace',
                              env=dict(os.environ, OCOMBO_JEV='off'))     # sem rede: o docstring promete (04/10/2026)

    def test_cli_nao_chama_o_jev(self):
        """O revisor viu estes testes chamarem o Jev por ssh: com o Jev ligado o motivo diz 'Jev:' ou 'sem Jev'."""
        self.assertNotIn('Jev', self._rodar('--plano', 'transcricao:44').stdout)

    def test_autor_vale_no_plano_que_abre_com_conferencia(self):
        """04/10/2026 (revisor): --autor no --plano era descartado em silencio e a conferencia de um autor opus saia
        opus (o autor caia em 'sonnet'). Agora vale para a conferencia que abre o plano; no resto, erro de uso."""
        r = self._rodar('--plano', 'conferencia:1', '--autor', 'opus')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertRegex(r.stdout, r'conferencia\s+x1\s+sonnet')
        self.assertEqual(self._rodar('--checar', 'conferencia:1=opus', '--autor', 'opus').returncode, 2)
        for ruim in (('--plano', 'transcricao:3,conferencia:3'), ('--tarefa', 'varredura')):
            r = self._rodar(*(ruim + ('--autor', 'opus')))
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn('--autor', r.stdout)

    def test_checar_sai_2_no_lote_de_topo(self):
        r = self._rodar('--checar', 'transcricao:44=fable')
        self.assertEqual(r.returncode, 2)
        self.assertIn('DINHEIRO', r.stdout)

    def test_plano_sai_0_e_mostra_o_relativo(self):
        r = self._rodar('--plano', 'transcricao:44,conferencia:44')
        self.assertEqual(r.returncode, 0)
        self.assertIn('30%', r.stdout)
        self.assertIn('Sommelier:', r.stdout)

    def test_erro_de_uso_sai_1(self):
        self.assertEqual(self._rodar('--tarefa', 'banana').returncode, 1)


if __name__ == '__main__':
    unittest.main()
