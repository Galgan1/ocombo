# -*- coding: utf-8 -*-
"""Testes puros de scripts/ram.py (v14, 04/10/2026): regra da RAM livre. Nao mede a maquina."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ram  # noqa: E402
import juiz  # noqa: E402


class TestVagas(unittest.TestCase):
    def test_pouca_ram_e_um_por_vez(self):
        self.assertEqual(ram.vagas(1200), 1)
        self.assertEqual(ram.vagas(0), 1)

    def test_folga_abre_vagas_pelo_custo_de_cada_claude(self):
        # reserva 1500 + 750 por vaga: 3,8 GB livres = 3 vagas
        self.assertEqual(ram.vagas(3800), 3)

    def test_teto_segura_o_paralelo(self):
        self.assertEqual(ram.vagas(20000), ram.TETO)
        self.assertEqual(ram.vagas(20000, teto=2), 2)

    def test_custo_explicito(self):
        self.assertEqual(ram.vagas(3500, por=500), 4)

    def test_sem_mcp_so_quando_aperta(self):
        self.assertTrue(ram.sem_mcp(1200))
        self.assertFalse(ram.sem_mcp(6000))

    def test_linha_do_estado(self):
        linha = ram.linha(3800)
        self.assertTrue(linha.startswith('RAM livre   : 3800 MB'))
        self.assertIn('vagas 3', linha)


class TestJuizSemMcp(unittest.TestCase):
    def setUp(self):
        self.antes = os.environ.pop('OCOMBO_SEM_MCP', None)

    def tearDown(self):
        os.environ.pop('OCOMBO_SEM_MCP', None)
        if self.antes is not None:
            os.environ['OCOMBO_SEM_MCP'] = self.antes

    def test_sem_variavel_a_linha_nao_muda(self):
        a = juiz.argumentos_claude('claude-sonnet-5-5', executavel='claude')
        self.assertNotIn('--strict-mcp-config', a)

    def test_com_variavel_o_juiz_sobe_sem_mcp(self):
        os.environ['OCOMBO_SEM_MCP'] = '1'
        a = juiz.argumentos_claude('claude-sonnet-5-5', executavel='claude')
        self.assertIn('--strict-mcp-config', a)
        i = a.index('--mcp-config')
        self.assertTrue(a[i + 1].endswith('mcp-vazio.json'))
        self.assertTrue(os.path.exists(a[i + 1]))


if __name__ == '__main__':
    unittest.main()
