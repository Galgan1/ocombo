# -*- coding: utf-8 -*-
"""Testes puros das ferramentas do espelho publico (nunca chamam git nem a rede).

Rodar: python -m unittest discover -s tools -p "test_*.py"   (prova_repo.py tambem roda isto)
"""
import os
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import prova_repo  # noqa: E402
import publicar  # noqa: E402

NOREPLY = '123+alguem@' + 'users.noreply.github.com'  # concatenado: a varredura do repo veta e-mail literal


class ProblemasGit(unittest.TestCase):
    """Privacidade nos METADADOS do git: autor/committer noreply, mensagem sem link privado nem e-mail."""

    def test_commit_limpo_passa(self):
        msg = 'ocombo v9: espelho\n\nCo-Authored-By: Claude <noreply@' + 'anthropic.com>\n'
        self.assertEqual(prova_repo.problemas_git([('abc', NOREPLY, NOREPLY, msg)]), [])

    def test_email_pessoal_do_autor_reprova(self):
        p = prova_repo.problemas_git([('abc', 'fulano@' + 'gmail.com', NOREPLY, 'x')])
        self.assertEqual(len(p), 1)
        self.assertIn('autor', p[0])
        self.assertIn('fulano@' + 'gmail.com', p[0])

    def test_email_pessoal_do_committer_reprova(self):
        p = prova_repo.problemas_git([('abc', NOREPLY, 'fulano@' + 'empresa.com.br', 'x')])
        self.assertEqual(len(p), 1)
        self.assertIn('committer', p[0])

    def test_link_de_sessao_na_mensagem_reprova(self):
        msg = 'v9\n\nClaude-Session: https://claude.ai/code/' + 'session_01ABC\n'
        p = prova_repo.problemas_git([('abc', NOREPLY, NOREPLY, msg)])
        self.assertEqual(len(p), 1)
        self.assertIn('sessao', p[0])

    def test_email_estranho_na_mensagem_reprova(self):
        p = prova_repo.problemas_git([('abc', NOREPLY, NOREPLY, 'Signed-off-by: X <x@' + 'dominio.org>')])
        self.assertEqual(len(p), 1)
        self.assertIn('x@' + 'dominio.org', p[0])

    def test_varios_commits_acumulam(self):
        regs = [('a1', 'a@' + 'gmail.com', 'a@' + 'gmail.com', 'https://claude.ai/code/' + 'session_1'),
                ('b2', NOREPLY, NOREPLY, 'ok')]
        self.assertEqual(len(prova_repo.problemas_git(regs)), 3)

    def test_parse_do_log(self):
        bruto = ('a1\x1f%s\x1f%s\x1fmsg um\nlinha 2\x1e' % (NOREPLY, NOREPLY)
                 + 'b2\x1fx@' + 'y.com\x1f%s\x1fmsg dois\x1e' % NOREPLY)
        regs = prova_repo.parse_log(bruto)
        self.assertEqual([r[0] for r in regs], ['a1', 'b2'])
        self.assertEqual(regs[0][3], 'msg um\nlinha 2')
        self.assertEqual(regs[1][1], 'x@' + 'y.com')


class Excluir(unittest.TestCase):
    """publicar.py: arquivos listados em 'excluir' do mapa nao viajam para o espelho."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        for rel in ('SKILL.md', 'references/a.md', 'references/dossie.md', 'scripts/x.py'):
            cam = os.path.join(self.d, rel)
            os.makedirs(os.path.dirname(cam), exist_ok=True)
            with open(cam, 'w', encoding='utf-8') as f:
                f.write('conteudo\n')

    def test_listar_sem_excluir(self):
        self.assertEqual(publicar.listar(self.d), ['SKILL.md', 'references/a.md', 'references/dossie.md', 'scripts/x.py'])

    def test_listar_com_excluir(self):
        r = publicar.listar(self.d, excluir=('references/dossie.md',))
        self.assertEqual(r, ['SKILL.md', 'references/a.md', 'scripts/x.py'])

    def test_mapa_carrega_excluir(self):
        cam = os.path.join(self.d, 'mapa.json')
        with open(cam, 'w', encoding='utf-8') as f:
            f.write('{"substituicoes": [["a", "b"]], "proibidos": ["x"], "excluir": ["references/dossie.md"]}')
        m = publicar.carregar_mapa(cam)
        self.assertEqual(m['excluir'], ['references/dossie.md'])
        self.assertEqual(publicar.carregar_mapa(None)['excluir'], [])

    def test_excluido_que_nao_existe_na_origem_e_problema(self):
        mapa = {'substituicoes': [], 'proibidos': [], 'excluir': ['references/nao-existe.md']}
        _, problemas = publicar.publicar(self.d, tempfile.mkdtemp(), mapa, checar=True)
        self.assertTrue(any('nao-existe.md' in p for p in problemas), problemas)


if __name__ == '__main__':
    unittest.main()
