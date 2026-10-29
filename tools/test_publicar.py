# -*- coding: utf-8 -*-
"""Testes puros do gerador do espelho (tools/publicar.py): corte de linhas privadas e substituicoes.

Rodar: python -m unittest discover -s tools -p "test_*.py"
"""
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import publicar  # noqa: E402


class Cortar(unittest.TestCase):
    """'cortar' do mapa: linha que casa o regex sai do espelho junto com as continuacoes indentadas."""

    def test_corta_bullet_e_continuacoes(self):
        texto = ('# Lista\n'
                 '- lição genérica que fica\n'
                 '- **Ciclo do projeto X (01/01/2026):** (a) coisa privada\n'
                 '  - **(b)** continuação indentada também sai\n'
                 '    ainda a mesma entrada\n'
                 '- outra lição genérica que fica\n')
        usadas = set()
        saida = publicar.cortar(texto, [r'^- \*\*Ciclo '], usadas)
        self.assertEqual(saida, '# Lista\n- lição genérica que fica\n- outra lição genérica que fica\n')
        self.assertEqual(usadas, {0})

    def test_regex_que_nao_casa_nao_entra_em_usadas(self):
        usadas = set()
        self.assertEqual(publicar.cortar('- nada aqui\n', [r'^- \*\*Ciclo '], usadas), '- nada aqui\n')
        self.assertEqual(usadas, set())

    def test_transformar_aplica_corte_so_em_md_e_txt(self):
        mapa_cortes = [r'^- \*\*Ciclo ']
        texto = b'- **Ciclo privado**\n  - detalhe\n- fica\n'
        usadas_s, usadas_c = set(), set()
        md = publicar.transformar(texto, 'references/x.md', [], usadas_s, mapa_cortes, usadas_c)
        self.assertEqual(md, b'- fica\n')
        py = publicar.transformar(texto, 'scripts/x.py', [], usadas_s, mapa_cortes, usadas_c)
        self.assertEqual(py, texto)

    def test_substituicao_continua_funcionando_com_corte(self):
        usadas_s, usadas_c = set(), set()
        saida = publicar.transformar(b'Ordem do Fulano\r\n', 'SKILL.md', [('Fulano', 'dono')], usadas_s, [], usadas_c)
        self.assertEqual(saida, b'Ordem do dono\n')
        self.assertEqual(usadas_s, {0})


if __name__ == '__main__':
    unittest.main()
