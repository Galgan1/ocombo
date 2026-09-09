# -*- coding: utf-8 -*-
"""Testes puros dos modulos v3 (triagem, rubrica, dupla, custo_historico, decisoes, iniciar).
Nunca chamam `claude`."""
import os
import shutil
import tempfile
import unittest

import custo_historico
import decisoes
import dupla
import iniciar
import rubrica
import triagem

SOLUCAO_OK = """=== ESTADO (fonte unica) ===
Lamina atual : juiz
=== TAREFA ===
x
=== RUBRICA (binaria, fixa entre rodadas) ===
C1. algo verificavel (comando)
C2. REGRESSAO: o que passava continua passando
=== SOLUCAO (rodada 1) ===
Evidencia em evidencias/ok.txt
"""


def _pasta(solucao, arquivos=()):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, 'solucao.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(solucao)
    for rel in arquivos:
        cam = os.path.join(d, rel)
        os.makedirs(os.path.dirname(cam), exist_ok=True)
        with open(cam, 'w', encoding='utf-8', newline='\n') as f:
            f.write('x\n')
    return d


class TestTriagem(unittest.TestCase):
    def test_passa_quando_tudo_presente(self):
        d = _pasta(SOLUCAO_OK, ['evidencias/ok.txt'])
        try:
            self.assertEqual(triagem.triagem(d), [])
        finally:
            shutil.rmtree(d)

    def test_acusa_caminho_inexistente_e_sem_regressao(self):
        d = _pasta(SOLUCAO_OK.replace('C2. REGRESSAO: o que passava continua passando\n', ''))
        try:
            probs = triagem.triagem(d)
            self.assertTrue(any('evidencias/ok.txt' in p for p in probs))
            self.assertTrue(any('REGRESS' in p.upper() for p in probs))
        finally:
            shutil.rmtree(d)

    def test_rubrica_pode_citar_arquivo_futuro(self):
        sol = SOLUCAO_OK.replace('C1. algo verificavel (comando)', 'C1. evidencias/so_na_entrega.txt existe')
        d = _pasta(sol, ['evidencias/ok.txt'])
        try:
            self.assertEqual(triagem.triagem(d), [])  # caminho na RUBRICA nao e afirmacao
        finally:
            shutil.rmtree(d)

    def test_acusa_sem_estado_e_sem_criterio(self):
        d = _pasta('=== TAREFA ===\nx\n=== RUBRICA ===\nnada numerado\n=== SOLUCAO ===\ny\n')
        try:
            probs = ' | '.join(triagem.triagem(d))
            self.assertIn('ESTADO', probs)
            self.assertIn('criterio', probs.lower())
        finally:
            shutil.rmtree(d)

    def test_manifesto_lista_arquivos_com_hash(self):
        d = _pasta(SOLUCAO_OK, ['evidencias/ok.txt', 'historico/solucao.r1.txt'])
        try:
            m = triagem.manifesto(d)
            self.assertIn('evidencias/ok.txt', m)
            self.assertNotIn('historico/', m)
            self.assertRegex(m, r'evidencias/ok.txt\s+2\s+[0-9a-f]{12}')
            self.assertTrue(os.path.exists(os.path.join(d, 'manifesto.txt')))
        finally:
            shutil.rmtree(d)


class TestRubrica(unittest.TestCase):
    def test_extrai_so_a_secao(self):
        r = rubrica.extrair_rubrica(SOLUCAO_OK)
        self.assertIn('C1.', r)
        self.assertIn('C2.', r)
        self.assertNotIn('=== SOLUCAO', r)
        self.assertNotIn('=== TAREFA', r)

    def test_prompt_pede_binario_verificavel_regressao(self):
        p = rubrica.prompt_critica('C1. x')
        for palavra in ['bin', 'verific', 'regress', 'escopo']:
            self.assertIn(palavra, p.lower())
        self.assertNotIn('VEREDICTO: APROVADO', p)  # critica, nao julgamento


class TestDupla(unittest.TestCase):
    def test_compara_por_criterio(self):
        a = '## C1\nPASS. ok\n## C2\nFAIL. faltou\n## C3\nPASS\nVEREDICTO: AJUSTE\n'
        b = '- C1: PASS\n- C2: PASS\n- C3: FAIL\nVEREDICTO: AJUSTE\n'
        c = dupla.comparar(a, b)
        self.assertEqual(c['por_criterio']['C1'], ('PASS', 'PASS'))
        self.assertEqual(c['por_criterio']['C2'], ('FAIL', 'PASS'))
        self.assertEqual(c['por_criterio']['C3'], ('PASS', 'FAIL'))
        self.assertAlmostEqual(c['taxa'], 1 / 3)
        md = dupla.concordancia_md(c, 'mA', 'mB')
        self.assertIn('C2', md)
        self.assertIn('33', md)

    def test_veredicto_por_criterio_ignora_texto_solto(self):
        self.assertEqual(dupla.por_criterio('C1 PASS — o C2 esta citado aqui\nC2: FAIL\n'),
                         {'C1': 'PASS', 'C2': 'FAIL'})

    def test_criterio_no_meio_da_frase_e_subcriterio(self):
        v = ('- **Achado 4 — C7 (2 âncoras com corpo vazio): PASS.**\n'
             '## C6.3 — juiz.py\nFAIL. faltou input=p\n'
             '- C1a: PASS | C1b: FAIL (o primeiro da linha manda)\n')
        self.assertEqual(dupla.por_criterio(v), {'C7': 'PASS', 'C6.3': 'FAIL', 'C1a': 'PASS'})

    def test_prosa_que_cita_fail_nao_e_rotulo(self):
        v = ('FAIL: **C3**". Em historico o C3 esta em **PASS**; os FAIL da r1 foram **C9 (3 achados)** e\n'
             '**C7 (1 achado)** — como confirma o proprio ESTADO ("4 achados"). Julguei os FAIL reais\n'
             '- **C7 — PASS (com ressalva registrada).** As duas ancoras ganharam corpo.\n')
        self.assertEqual(dupla.por_criterio(v), {'C3': 'PASS', 'C7': 'PASS'})

    def test_discordancias_pro_e_contra_executor(self):
        """v6: A (Sonnet) FAIL e B (Opus) PASS = B discordou A FAVOR do executor."""
        c = dupla.comparar('CRITERIO C1: FAIL\nCRITERIO C2: PASS\nCRITERIO C3: PASS\n',
                           'CRITERIO C1: PASS\nCRITERIO C2: FAIL\nCRITERIO C3: PASS\n')
        disc = dupla.discordancias(c)
        self.assertEqual(disc['pro_executor'], ['C1'])
        self.assertEqual(disc['contra_executor'], ['C2'])

    def test_balanco_alerta_acima_de_tres_em_dez(self):
        """v6: >3 discordancias a favor do executor nos ultimos 10 ciclos = trocar o juiz padrao."""
        evs = [{'tipo': 'dupla', 'instancia': 'i%d' % i, 'pro_executor': 1 if i >= 8 else 0, 'contra_executor': 0}
               for i in range(12)]  # 12 ciclos; so os 10 ultimos contam (i=2..11) e 4 deles discordam
        evs.append({'tipo': 'veredicto', 'instancia': 'x'})  # outro tipo nao conta
        b = dupla.balanco(evs, janela=10)
        self.assertEqual(b['ciclos'], 10)
        self.assertEqual(b['pro_executor'], 4)
        self.assertTrue(b['alerta'])
        self.assertFalse(dupla.balanco(evs[:2], janela=10)['alerta'])


class TestCustoHistorico(unittest.TestCase):
    def test_tabela_por_instancia(self):
        linhas = [
            '2026-09-05T21:15:57 ocombo-v2 r1 claude-sonnet-5 in=32 out=16548 cache_read=1 cache_write=2 usd=0.82 s=199.9 turnos=29',
            '2026-09-05T21:20:22 ocombo-v2 r2 claude-sonnet-5 in=30 out=10357 cache_read=1 cache_write=2 usd=0.55 s=136.4 turnos=26',
            '2026-09-05T22:00:00 outro r1 claude-haiku-4-5 sem usage',
        ]
        t = custo_historico.tabela(linhas)
        self.assertIn('ocombo-v2', t)
        self.assertIn('1.37', t)      # total usd
        self.assertIn('0.69', t)      # usd por rodada (1.37/2 = 0.685 -> 0.69)
        self.assertIn('outro', t)
        self.assertIn('TOTAL', t)

    def test_parse_linha_sem_usage(self):
        self.assertIsNone(custo_historico.parse('x inst r1 m sem usage')['usd'])


class TestDecisoes(unittest.TestCase):
    def test_acha_linha_com_marcador_e_palavra(self):
        textos = {
            'a.md': 'Em 04/09 o dono decidiu: WhatsApp agendado e sempre pela VPS.\nlinha sem nada\n',
            'b.md': 'O gato subiu no telhado do whatsapp.\n',
        }
        r = decisoes.buscar(textos, ['whatsapp'])
        self.assertEqual(len(r), 1)
        self.assertIn('a.md', r[0])
        self.assertIn('VPS', r[0])

    def test_sem_acento_e_caixa(self):
        textos = {'c.md': 'Regra: PUBLICAÇÃO só com sim explícito.\n'}
        self.assertEqual(len(decisoes.buscar(textos, ['publicacao'])), 1)


class TestIniciar(unittest.TestCase):
    def test_monta_solucao_com_rubrica_e_herdado(self):
        modelo = '=== ESTADO ===\nContexto herdado inviolavel (decisoes do dono ja fechadas): H1 ..., H2 ...\n=== RUBRICA (binaria, fixa entre rodadas) ===\nC1. ...\nC9. REGRESSAO: x\n=== SOLUCAO ===\n'
        s = iniciar.montar_solucao(modelo, 'C1. bot responde /start\nC2. REGRESSAO: suite verde\n',
                                   ['- [a.md] decidiu X'])
        self.assertIn('bot responde /start', s)
        self.assertIn('decidiu X', s)
        self.assertNotIn('C1. ...', s)
        self.assertLess(s.index('decidiu X'), s.index('=== RUBRICA'))

    def test_nao_sobrescreve_solucao_existente(self):
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, 'solucao.txt'), 'w', encoding='utf-8') as f:
                f.write('JA EXISTE')
            _, mud1 = iniciar.iniciar(d, tipo='skill', palavras=[], rodar_loop_init=False, memoria_dir=d)
            _, mud2 = iniciar.iniciar(d, tipo='skill', palavras=[], rodar_loop_init=False, memoria_dir=d)
            self.assertGreater(mud1, 0)
            self.assertEqual(mud2, 0)  # idempotente: 2a execucao = 0 mudanca
            with open(os.path.join(d, 'solucao.txt'), encoding='utf-8') as f:
                self.assertEqual(f.read(), 'JA EXISTE')
            self.assertTrue(os.path.isdir(os.path.join(d, 'evidencias')))
            self.assertTrue(os.path.exists(os.path.join(d, 'prova.bat')))
        finally:
            shutil.rmtree(d)

    def test_pasta_que_parece_opcao_nao_cria_instancia(self):
        # 08/09/2026: `python iniciar.py --help` criou uma pasta "--help" (com solucao.txt e pontes) dentro da skill
        import subprocess
        import sys as _sys
        d = tempfile.mkdtemp()
        try:
            r = subprocess.run([_sys.executable, os.path.join(os.path.dirname(os.path.abspath(iniciar.__file__)), 'iniciar.py'), '--help'],
                               cwd=d, stdin=subprocess.DEVNULL, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertEqual(os.listdir(d), [], 'nao pode criar pasta nenhuma')
            self.assertIn('Uso:', r.stdout)
        finally:
            shutil.rmtree(d)


if __name__ == '__main__':
    unittest.main()
