# -*- coding: utf-8 -*-
"""Testes puros de qualidade.py e smoke_web.py (nao chamam ruff, eslint nem playwright).
Rodar: python -m unittest -q test_qualidade"""
import json
import os
import shutil
import tempfile
import unittest

import qualidade

NL = chr(10)
import smoke_web


class TestListar(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        for rel in ['a.py', 'b.js', 'c.mjs', 'lib.min.js', 'node_modules/x.js', '.git/y.py', 'sub/d.py', 'historico/e.js']:
            cam = os.path.join(self.d, rel)
            os.makedirs(os.path.dirname(cam), exist_ok=True)
            open(cam, 'w').close()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_py_ignora_pastas(self):
        rel = [os.path.relpath(p, self.d) for p in qualidade.listar(self.d, ('.py',))]
        self.assertEqual(rel, ['a.py', os.path.join('sub', 'd.py')])

    def test_js_ignora_node_modules_historico_e_min(self):
        rel = [os.path.relpath(p, self.d) for p in qualidade.listar(self.d, qualidade.EXT_JS)]
        self.assertEqual(rel, ['b.js', 'c.mjs'])

    def test_minificado_por_linha_longa(self):
        cam = os.path.join(self.d, 'bundle.js')
        open(cam, 'w').write('var a=1;' * 1000 + '\n')
        self.assertTrue(qualidade.minificado(cam))
        self.assertFalse(qualidade.minificado(os.path.join(self.d, 'b.js')))

    def test_minificado_com_cabecalho_de_licenca_antes_da_linha_longa(self):
        # bundle do Vite: 20 linhas curtas de licenca e a linha longa depois (public/assets/index-*.js, 06/09/2026)
        cam = os.path.join(self.d, 'index-Abc123.js')
        open(cam, 'w').write('/**' + NL + (' * @license React' + NL) * 20 + ' */' + NL + 'var a=1;' * 1000 + NL)
        self.assertTrue(qualidade.minificado(cam))

    def test_listar_pula_dist_com_sufixo(self):
        os.makedirs(os.path.join(self.d, 'dist-prod', 'assets'))
        os.makedirs(os.path.join(self.d, 'dist-sandbox'))
        open(os.path.join(self.d, 'dist-prod', 'assets', 'x.js'), 'w').write('x')
        open(os.path.join(self.d, 'dist-sandbox', 'y.js'), 'w').write('y')
        rel = [os.path.relpath(p, self.d) for p in qualidade.listar(self.d, qualidade.EXT_JS)]
        self.assertEqual(rel, ['b.js', 'c.mjs'])

    def test_sem_ignorados_remove_por_caminho_normalizado(self):
        arqs = [os.path.join(self.d, 'b.js'), os.path.join(self.d, 'db', 'caixa.js')]
        ign = [os.path.join(self.d, 'db', 'caixa.js').replace(os.sep, '/')]
        self.assertEqual(qualidade.sem_ignorados(arqs, ign), [arqs[0]])
        self.assertEqual(qualidade.sem_ignorados(arqs, []), arqs)

    def test_ignorados_pelo_git_fora_de_repo_e_lista_vazia(self):
        self.assertEqual(qualidade.ignorados_pelo_git(self.d, [os.path.join(self.d, 'b.js')]), [])
        self.assertEqual(qualidade.ignorados_pelo_git(self.d, []), [])

    def test_lotes_divide_sem_perder_nem_repetir(self):
        itens = list(range(250))
        ls = qualidade.lotes(itens, 120)
        self.assertEqual([len(l) for l in ls], [120, 120, 10])
        self.assertEqual(sum(ls, []), itens)
        self.assertEqual(qualidade.lotes([], 120), [])

    def test_repo_esm_le_package_json(self):
        self.assertFalse(qualidade.repo_esm(self.d))
        open(os.path.join(self.d, 'package.json'), 'w').write('{"type": "module"}')
        self.assertTrue(qualidade.repo_esm(self.d))


class TestResumir(unittest.TestCase):
    def test_ruff(self):
        j = json.dumps([{'filename': 'x.py', 'location': {'row': 3}, 'code': 'F821', 'message': 'Undefined name `foo`'}])
        self.assertEqual(qualidade.resumir_ruff(j), [('x.py', 3, 'F821', 'Undefined name `foo`')])

    def test_ruff_vazio_e_ilegivel(self):
        self.assertEqual(qualidade.resumir_ruff(''), [])
        self.assertEqual(qualidade.resumir_ruff('nao e json')[0][2], 'RUFF-JSON')

    def test_eslint_so_erros(self):
        j = json.dumps([{'filePath': 'a.js', 'messages': [
            {'severity': 2, 'line': 7, 'ruleId': 'no-undef', 'message': "'lerFatos' is not defined."},
            {'severity': 1, 'line': 9, 'ruleId': 'no-unused-vars', 'message': 'aviso'}]}])
        self.assertEqual(qualidade.resumir_eslint(j), [('a.js', 7, 'no-undef', "'lerFatos' is not defined.")])

    def test_eslint_fatal_sem_ruleId(self):
        j = json.dumps([{'filePath': 'a.js', 'messages': [{'severity': 2, 'line': 1, 'ruleId': None, 'message': 'Parsing error'}]}])
        self.assertEqual(qualidade.resumir_eslint(j)[0][2], 'fatal')

    def test_por_regra_ordena_por_frequencia(self):
        achados = [('a', 1, 'no-unused-vars', ''), ('b', 2, 'no-undef', ''), ('c', 3, 'no-unused-vars', '')]
        self.assertEqual(qualidade.por_regra(achados), [('no-unused-vars', 2), ('no-undef', 1)])


class TestConfig(unittest.TestCase):
    def test_config_eslint_existe_sem_import_de_pacote(self):
        t = open(qualidade.CONFIG_ESLINT, encoding='utf-8').read()
        self.assertIn("'no-undef': 'error'", t)
        self.assertIn("'no-unused-vars'", t)
        self.assertNotIn("from '@eslint/js'", t)  # armadilha medida: import resolve relativo a config
        self.assertIn('OCOMBO_ESLINT_MODULE', t)


class TestSmokeResumo(unittest.TestCase):
    def test_passou(self):
        rel = {'suites': [{'specs': [{'tests': [{'results': [{'status': 'passed'}]}]}]}]}
        self.assertEqual(smoke_web.resumo(json.dumps(rel)), (1, 0, []))

    def test_falhou_com_mensagem(self):
        rel = {'suites': [{'suites': [{'specs': [{'tests': [{'results': [
            {'status': 'failed', 'error': {'message': 'erros de JS no console\nexpected []'}}]}]}]}]}]}
        self.assertEqual(smoke_web.resumo(json.dumps(rel)), (0, 1, ['erros de JS no console']))

    def test_ilegivel(self):
        self.assertEqual(smoke_web.resumo('x')[2], ['relatorio ilegivel'])

    def test_assets_existem(self):
        for a in ('smoke.spec.js', 'playwright.config.js'):
            self.assertTrue(os.path.exists(os.path.join(smoke_web.ASSETS, a)), a)


if __name__ == '__main__':
    unittest.main()
