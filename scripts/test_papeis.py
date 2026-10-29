# -*- coding: utf-8 -*-
"""Testes puros da v10: porta de entrada (quais laminas) e papeis como subagentes.

Nao chamam `claude`, nao pedem rede e nao tocam ~/.claude (o destino da instalacao e um tmpdir).
"""
import os
import shutil
import tempfile
import unittest

import instalar_agentes as ia
import porta

AQUI = os.path.dirname(os.path.abspath(__file__))


class TestPorta(unittest.TestCase):
    def test_reparo_pontual_dispensa_a_grelha(self):
        d = porta.decidir(pedido='conserta o acento do relatorio', reparo=True, arquivos=1)
        self.assertFalse(d['grelha'])
        self.assertEqual(d['laminas'], ['executor', 'juiz'])
        self.assertEqual(d['papeis']['grelha'], 'dispensada')
        self.assertIn('1 arquivo(s)', '; '.join(d['motivos']))

    def test_peca_nova_obriga_grelha(self):
        d = porta.decidir(pedido='criar um painel novo do zero', arquivos=2)
        self.assertTrue(d['grelha'])
        self.assertEqual(d['laminas'][0], 'grelha')

    def test_palavra_de_producao_levanta_regua_e_lamina(self):
        d = porta.decidir(pedido='deploy do bot na VPS', reparo=True, arquivos=1)
        self.assertIn('producao', d['regua'])
        self.assertTrue(d['grelha'])
        self.assertIn('producao', d['laminas'])

    def test_escopo_largo_obriga_grelha(self):
        d = porta.decidir(pedido='ajusta os modulos', reparo=True, arquivos=porta.LIMIAR_ARQUIVOS)
        self.assertTrue(d['grelha'])

    def test_sem_criterio_de_pronto_obriga_grelha(self):
        d = porta.decidir(pedido='melhora isso ai', reparo=True, arquivos=1, criterio_de_pronto=False)
        self.assertTrue(d['grelha'])

    def test_decisao_em_aberto_obriga_grelha(self):
        d = porta.decidir(pedido='troca a fila', reparo=True, arquivos=1, decisoes_abertas=1)
        self.assertTrue(d['grelha'])

    def test_ordem_nao_desliga_portao_quando_a_regua_e_tocada(self):
        d = porta.decidir(pedido='apagar o backup velho', reparo=True, arquivos=1, forcar='sem-grelha')
        self.assertFalse(d['valida'])
        self.assertTrue(d['grelha'])
        self.assertIn('Portao nao se desliga', d['recusa'])

    def test_ordem_dispensa_mas_fica_escrito_o_que_ela_venceu(self):
        d = porta.decidir(pedido='reescrever o parser', arquivos=2, forcar='sem-grelha')
        self.assertFalse(d['grelha'])
        self.assertIn('apesar de', '; '.join(d['motivos']))

    def test_forcar_grelha_vence_reparo(self):
        d = porta.decidir(pedido='troca o timeout', reparo=True, arquivos=1, forcar='grelha')
        self.assertTrue(d['grelha'])

    def test_regua_desconhecida_invalida(self):
        d = porta.decidir(pedido='x', reparo=True, arquivos=1, regua=['banana'])
        self.assertFalse(d['valida'])

    def test_bloco_do_estado_tem_as_tres_linhas(self):
        linhas = porta.decidir(pedido='x', reparo=True, arquivos=1)['estado'].split('\n')
        self.assertEqual(len(linhas), 3)
        self.assertTrue(linhas[0].startswith('Porta: GRELHA='))
        self.assertTrue(linhas[1].startswith('Laminas: '))
        self.assertTrue(linhas[2].startswith('Papeis: '))

    def test_main_exit_0_e_2(self):
        self.assertEqual(porta.main(['--pedido', 'conserta o typo', '--reparo', '--arquivos', '1']), 0)
        self.assertEqual(porta.main(['--pedido', 'x', '--regua', 'dinheiro', '--forcar', 'sem-grelha']), 2)

    def test_pistas_ignoram_acento(self):
        self.assertIn('producao', porta.pistas('sobe para producao')['regua'])
        self.assertIn('producao', porta.pistas('sobe para produção')['regua'])


class TestPapeis(unittest.TestCase):
    def test_os_tres_papeis_existem_e_sao_validos(self):
        probs, _ = ia.estado(destino=tempfile.mkdtemp())
        self.assertEqual(probs, [], '; '.join(probs))

    def test_juiz_sem_ferramenta_de_escrita(self):
        ruim = ('---\nname: ocombo-juiz\ndescription: Papel juiz do combo com uma descricao longa o '
                'bastante para passar do limite de oitenta caracteres exigido. Use sempre.\n'
                'tools: Read, Write, Bash\nmodel: sonnet\n---\ncorpo\n')
        probs = ia.validar(ruim, 'ocombo-juiz')
        self.assertTrue(any('escrita' in p for p in probs), probs)
        self.assertTrue(any('negar explicitamente' in p for p in probs), probs)

    def test_juiz_nao_pode_herdar_o_modelo_do_executor(self):
        ruim = ('---\nname: ocombo-juiz\ndescription: Papel juiz do combo com uma descricao longa o '
                'bastante para passar do limite de oitenta caracteres exigido. Use sempre.\n'
                'tools: Read, Bash\ndisallowedTools: Edit, Write, NotebookEdit\nmodel: inherit\n---\nx\n')
        self.assertTrue(any('cross-model' in p for p in ia.validar(ruim, 'ocombo-juiz')))

    def test_name_tem_de_bater_com_o_arquivo(self):
        ruim = ('---\nname: outro\ndescription: Descricao longa o bastante para passar do limite de '
                'oitenta caracteres exigido pelo portao. Use quando quiser.\nmodel: inherit\n---\nx\n')
        self.assertTrue(any('name do frontmatter' in p for p in ia.validar(ruim, 'ocombo-grelha')))

    def test_instalar_e_verificar(self):
        dest = tempfile.mkdtemp()
        try:
            probs, escritos = ia.instalar(dest)
            self.assertEqual(probs, [])
            self.assertEqual(sorted(escritos), sorted(ia.PAPEIS))
            self.assertEqual(ia.main(['--destino', dest, '--verificar']), 0)
            self.assertEqual(ia.instalar(dest)[1], [])  # idempotente
            with open(os.path.join(dest, 'ocombo-juiz.md'), 'ab') as f:
                f.write(b'mexeram aqui\n')
            self.assertEqual(ia.main(['--destino', dest, '--verificar']), 1)
        finally:
            shutil.rmtree(dest, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
