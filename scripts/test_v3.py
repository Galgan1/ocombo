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
            '2026-09-05T21:15:57 ocombo-v2 r1 claude-sonnet-5-5 in=32 out=16548 cache_read=1 cache_write=2 usd=0.82 s=199.9 turnos=29',
            '2026-09-05T21:20:22 ocombo-v2 r2 claude-sonnet-5-5 in=30 out=10357 cache_read=1 cache_write=2 usd=0.55 s=136.4 turnos=26',
            '2026-09-05T22:00:00 outro r1 claude-haiku-4-5-20251001 sem usage',
        ]
        t = custo_historico.tabela(linhas)
        self.assertIn('ocombo-v2', t)
        self.assertIn('1.37', t)      # total usd
        self.assertIn('0.69', t)      # usd por rodada (1.37/2 = 0.685 -> 0.69)
        self.assertIn('outro', t)
        self.assertIn('TOTAL', t)

    def test_por_modelo_agrupa_modelo_papel_effort(self):
        linhas = [
            '2026-10-02T10:00:00 a r1 claude-sonnet-5-5 in=1 out=2 cache_read=0 cache_write=0 usd=0.40 s=60.0 turnos=10',
            '2026-10-02T10:05:00 a r2 claude-sonnet-5-5 in=1 out=2 cache_read=0 cache_write=0 usd=0.60 s=80.0 turnos=10 effort=high',
            '2026-10-02T10:06:00 a dupla claude-opus-5-5 in=1 out=2 cache_read=0 cache_write=0 usd=1.00 s=100.0 turnos=5',
            '2026-10-02T10:07:00 a r3 - prova VERMELHA - juiz nao chamado (0 tokens)',
        ]
        t = custo_historico.por_modelo(linhas)
        self.assertIn('claude-sonnet-5-5            juiz     -          1     0.40      60     10.0     0.040      6.0', t)
        self.assertIn('claude-sonnet-5-5            juiz     high       1     0.60      80     10.0     0.060      8.0', t)
        self.assertIn('claude-opus-5-5              dupla    -          1     1.00     100      5.0     0.200     20.0', t)
        self.assertNotIn('VERMELHA', t)

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



# v12 (29/09/2026): pacotes por natureza. Os tipos novos (texto, pesquisa, desenho, acao) ganham a linha
# Pacote no ESTADO; os 5 tipos antigos saem byte a byte como antes (o caminho de codigo nao muda).
_SKILL_V12 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TIPOS_ANTIGOS = ('bot', 'site', 'script-agendado', 'receita-maquina', 'skill')
_TIPOS_NOVOS = ('texto', 'pesquisa', 'desenho', 'acao')
_LAMINA_NOVA = 'Lamina atual : [grelha | juiz | akita=portao antes da peca | producao so se a regua pedir]'


def _solucao_gerada(tipo, modo=0):
    d = tempfile.mkdtemp()
    mem = tempfile.mkdtemp()
    try:
        iniciar.iniciar(os.path.join(d, 'inst'), tipo, rodar_loop_init=False, memoria_dir=mem, modo=modo)
        with open(os.path.join(d, 'inst', 'solucao.txt'), 'rb') as f:
            return f.read().decode('utf-8')
    finally:
        shutil.rmtree(d)
        shutil.rmtree(mem)


def _criterios(texto):
    """[(numero, corpo)] de cada linha 'Cn. corpo' da rubrica."""
    import re
    return [(int(m.group(1)), m.group(2)) for m in re.finditer(r'^C(\d+)\. (.*)$', texto, re.M)]


def _ler_skill(rel):
    with open(os.path.join(_SKILL_V12, rel), 'rb') as f:
        return f.read().decode('utf-8')


class TestPacotesV12(unittest.TestCase):
    def test_tipos_novos_geram_linha_pacote_depois_de_papeis(self):
        for tipo in _TIPOS_NOVOS:
            linhas = _solucao_gerada(tipo).split('\n')
            pacote = 'Pacote       : %s (ler references/pacotes/%s.md)' % (tipo, tipo)
            self.assertIn(pacote, linhas, tipo)
            i = linhas.index(pacote)
            self.assertTrue(linhas[i - 1].startswith('Papeis       :'), (tipo, linhas[i - 1]))
            self.assertIn(_LAMINA_NOVA, linhas, tipo)
            self.assertNotIn('Lamina atual : [grelha | juiz | tdd | producao]', linhas, tipo)

    def test_tipos_novos_trazem_a_rubrica_do_tipo(self):
        for tipo in _TIPOS_NOVOS:
            s = _solucao_gerada(tipo)
            self.assertIn(_ler_skill('assets/rubricas/%s.txt' % tipo).split('\n')[1], s, tipo)

    def test_tipos_antigos_saem_como_antes(self):
        modelo = _ler_skill('assets/solucao.modelo.txt')
        for tipo in _TIPOS_ANTIGOS:
            for modo in (0, 7, 'f1'):
                s = _solucao_gerada(tipo, modo)
                self.assertNotIn('Pacote       :', s, tipo)
                self.assertNotIn('references/pacotes/', s, tipo)
                rub = _ler_skill('assets/rubricas/%s.txt' % tipo)
                antes = iniciar.aplicar_modo(iniciar.montar_solucao(modelo, rub, []),
                                             iniciar.modos.perfil(modo))
                self.assertEqual(s, antes, (tipo, modo))

    def test_aplicar_pacote_so_age_nos_tipos_novos(self):
        modelo = _ler_skill('assets/solucao.modelo.txt')
        for tipo in _TIPOS_ANTIGOS + ('xyz',):
            self.assertEqual(iniciar.aplicar_pacote(modelo, tipo), modelo, tipo)
        novo = iniciar.aplicar_pacote(modelo, 'texto')
        self.assertEqual(novo.count('Pacote       :'), 1)
        self.assertEqual(len(novo.split('\n')), len(modelo.split('\n')) + 1)
        self.assertEqual(iniciar.aplicar_pacote('sem estado nenhum\n', 'texto'), 'sem estado nenhum\n')

    def test_tipos_lista_e_padrao(self):
        import inspect
        self.assertEqual(set(iniciar.TIPOS), set(_TIPOS_ANTIGOS + _TIPOS_NOVOS))
        self.assertEqual(len(iniciar.TIPOS), 9)
        self.assertEqual(inspect.signature(iniciar.iniciar).parameters['tipo'].default, 'skill')
        self.assertIn('texto|pesquisa|desenho|acao', iniciar.__doc__)

    def test_tipo_invalido_continua_saindo_2(self):
        import subprocess
        import sys as _sys
        d = tempfile.mkdtemp()
        try:
            r = subprocess.run([_sys.executable, os.path.join(_SKILL_V12, 'scripts', 'iniciar.py'),
                                os.path.join(d, 'inst'), '--tipo', 'xyz'],
                               stdin=subprocess.DEVNULL, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, 'inst')))
        finally:
            shutil.rmtree(d)

    def test_reguas_novas_no_formato_do_c3(self):
        skill = dict(_criterios(_ler_skill('assets/rubricas/skill.txt')))
        c0 = skill[0]
        escalada = [c for c in skill.values() if c.startswith('ESCALADA:')][0]
        sommelier = [c for c in skill.values() if c.startswith('SOMMELIER:')][0]
        for tipo in _TIPOS_NOVOS:
            crit = _criterios(_ler_skill('assets/rubricas/%s.txt' % tipo))
            corpos = [c for _, c in crit]
            self.assertEqual([n for n, _ in crit], list(range(len(crit))), tipo)  # C0..Cn sem buraco
            self.assertEqual(corpos[0], c0, tipo)
            self.assertIn(escalada, corpos, tipo)
            self.assertIn(sommelier, corpos, tipo)
            self.assertTrue(corpos[-1].startswith('REGRESSAO:'), tipo)
            qualidade = corpos[1:-1]
            qualidade = [c for c in qualidade if c not in (escalada, sommelier)]
            self.assertEqual(len(qualidade), len(corpos) - 4, tipo)
            leitura = [c for c in qualidade if c.startswith('[LEITURA]')]
            medido = [c for c in qualidade if c.startswith('[MEDIDO]')]
            self.assertEqual(len(leitura) + len(medido), len(qualidade), tipo)
            self.assertLessEqual(3 * len(leitura), len(qualidade), tipo)   # H8: teto de 1/3
            for c in medido:
                self.assertIn('exit', c, (tipo, c[:60]))
            for c in leitura:
                self.assertIn('tier', c, (tipo, c[:60]))
                self.assertIn('cit', c, (tipo, c[:60]))
                self.assertIn('FAIL', c, (tipo, c[:60]))
            for c in corpos:
                if 'jev' in c.lower():
                    self.assertIn('opcional', c.lower(), (tipo, c[:60]))   # H9: Jev nunca e portao

    def test_cinco_pacotes_existem(self):
        for nome in ('codigo',) + _TIPOS_NOVOS:
            self.assertTrue(os.path.exists(os.path.join(_SKILL_V12, 'references', 'pacotes', nome + '.md')), nome)
        for tipo in _TIPOS_NOVOS:
            t = _ler_skill('references/pacotes/%s.md' % tipo).lower()
            for palavra in ('akita', 'producao-senior', 'ledger', 'misto', '[leitura]', 'codigo'):
                self.assertIn(palavra, t.replace('código', 'codigo'), (tipo, palavra))

    def test_codigo_md_guarda_as_ferramentas_de_teste(self):
        t = _ler_skill('references/pacotes/codigo.md')
        for trecho in ('scripts/qualidade.py <repo>', 'scripts/smoke_web.py <url> --texto <esperado>',
                       'Smoke pós-deploy', 'resolvem relativo ao'):
            self.assertIn(trecho, t)
        s = _ler_skill('SKILL.md')
        self.assertIn('references/pacotes/codigo.md', s)
        self.assertNotIn('Armadilha medida na estreia: config do eslint', s)

    # Rodada 2 (conferentes, 29/09/2026): regua aplicada a instancias reais nao era julgavel.
    def _criterio(self, tipo, rotulo):
        for _, c in _criterios(_ler_skill('assets/rubricas/%s.txt' % tipo)):
            if rotulo in c:
                return c
        self.fail('%s sem %s' % (tipo, rotulo))

    def test_texto_c2_define_item_e_aceita_rodape_com_mapa(self):
        c = self._criterio('texto', 'FATO COM FONTE').lower()
        for trecho in ('item =', 'rodape', 'mapa', 'numero do item', 'fail'):
            self.assertIn(trecho, c, trecho)
        self.assertIn('rodape', _ler_skill('references/pacotes/texto.md').lower())

    def test_acao_preve_acao_sem_tela(self):
        c1 = self._criterio('acao', 'CAPTURA').lower()
        c5 = self._criterio('acao', 'NAVEGADOR DECLARADO').lower()
        for trecho in ('sem tela', 'log'):
            self.assertIn(trecho, c1, trecho)
        self.assertIn('n/a', c5)
        self.assertIn('sem tela', _ler_skill('references/pacotes/acao.md').lower())

    def test_vermelho_anterior_ao_verde_conferido_por_comando(self):
        for tipo, rotulo in (('desenho', 'LIMIAR-ESCRITO'), ('texto', 'FORMA'),
                             ('acao', 'STRINGS ESPERADAS')):
            c = self._criterio(tipo, rotulo).lower()
            self.assertIn('anterior ao verde', c, tipo)

    # Rodada 2 (maestro, 29/09/2026): voz e custo da regua de texto reprovariam peca sem defeito.
    def test_texto_c3_voz_so_na_peca_em_nome_do_dono(self):
        c = self._criterio('texto', 'VOZ DO DONO').lower()
        for trecho in ('em nome do dono', 'n/a', 'motivo'):
            self.assertIn(trecho, c, trecho)
        self.assertIn('em nome do dono', _ler_skill('references/pacotes/texto.md').lower())

    def test_texto_c4_mira_o_custo_da_esteira(self):
        c = self._criterio('texto', 'SEM CUSTO').lower()
        self.assertNotIn('custou', c)
        self.assertNotIn('gastei', c)
        for trecho in ('custo da esteira', 'custo\\.log', 'assunto'):
            self.assertIn(trecho, c, trecho)


class TestDuplaSegueOModo(unittest.TestCase):
    """17/10/2026 (ciclo opala): o dupla.py chamava o juiz B sem effort e sem timeout; no modo 10 o B rodava
    no effort padrao da CLI e com 900 s, enquanto o A rodava em xhigh com 1800 s."""

    AUSENTE = 'ausente'

    def _rodar(self, modo, **kw):
        from unittest import mock
        d = _pasta(SOLUCAO_OK)
        with open(os.path.join(d, 'veredicto.md'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('CRITERIO C1: PASS\nCRITERIO C2: PASS\nVEREDICTO: APROVADO\n')
        chamadas = []

        def falso(pasta, modelo, p, arquivo, timeout=self.AUSENTE, tentativas=2, effort=self.AUSENTE):
            chamadas.append({'modelo': modelo, 'timeout': timeout, 'effort': effort})
            return 'CRITERIO C1: PASS\nCRITERIO C2: PASS\nVEREDICTO: APROVADO\n', {}, 'ok'

        try:
            with mock.patch.dict(os.environ, {'OCOMBO_MODO': modo}), \
                    mock.patch.object(dupla.juiz, 'chamar_juiz', falso), \
                    mock.patch.object(dupla.juiz, 'registrar_custo', lambda *a, **k: ''), \
                    mock.patch.object(dupla, '_ledger_dupla', lambda *a, **k: None):
                rc = dupla.rodar(d, 'claude-opus-5-5', **kw)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        return rc, chamadas

    def test_modo_10_passa_medium_e_1800_ao_juiz_b(self):
        # 29/10/2026 (uso enxuto consolidado): o modo 10 passa juiz_effort medium (era xhigh) e mantem o timeout de 1800 s.
        rc, ch = self._rodar('10')
        self.assertEqual(rc, 0)
        self.assertEqual((ch[0]['effort'], ch[0]['timeout']), ('medium', 1800))

    def test_effort_e_timeout_explicitos_vencem_o_modo(self):
        rc, ch = self._rodar('10', effort='high', timeout=600)
        self.assertEqual((ch[0]['effort'], ch[0]['timeout']), ('high', 600))

    def test_modo_0_fica_como_antes(self):
        rc, ch = self._rodar('0')
        self.assertEqual((ch[0]['effort'], ch[0]['timeout']), (None, dupla.juiz.TIMEOUT_PADRAO))

    def test_log_da_dupla_diz_o_modo_o_effort_e_o_timeout(self):
        # 17/10/2026 (plano opala r2, juiz B C9): o log da dupla nao provava OCOMBO_MODO=10 nem o timeout de 1800 s
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self._rodar('10')
        primeira = buf.getvalue().splitlines()[0]
        for trecho in ('(modo opala)', 'effort medium', 'timeout 1800', 'claude-opus-5-5'):
            self.assertIn(trecho, primeira)


class TestDuplaRodadaPorDiff(unittest.TestCase):
    """17/10/2026 (ciclo opala, plano r1: A APROVADO, B AJUSTE em C2/C9/C10): na r2 o dupla.py montava o prompt so
    com os FAIL do juiz A da r1 (nenhum) e chamava o veredicto do A de "seu veredicto anterior"; o B nunca mais
    julgaria os FAIL dele. Agora: o B julga FAIL + N/A do A E os dele, le o proprio veredicto anterior e guarda o
    seu em historico/veredicto.<modeloB>.rN.md."""

    B = 'claude-opus-5-5'

    def _instancia(self, b_anterior=True):
        d = _pasta(SOLUCAO_OK)
        h = os.path.join(d, 'historico')
        os.makedirs(h)
        for nome, txt in (('solucao.r1.txt', SOLUCAO_OK), ('solucao.r2.txt', SOLUCAO_OK),
                          ('veredicto.r1.md', 'CRITERIO C1: PASS\nCRITERIO C2: N/A\nVEREDICTO: APROVADO\n')):
            with open(os.path.join(h, nome), 'w', encoding='utf-8', newline='\n') as f:
                f.write(txt)
        if b_anterior:
            with open(os.path.join(h, 'veredicto.%s.r1.md' % self.B), 'w', encoding='utf-8', newline='\n') as f:
                f.write('CRITERIO C1: FAIL\nCRITERIO C2: N/A\nVEREDICTO: AJUSTE\n')
        with open(os.path.join(d, 'delta.patch'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n')
        with open(os.path.join(d, 'veredicto.md'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('CRITERIO C1: PASS\nCRITERIO C2: PASS\nVEREDICTO: APROVADO\n')
        return d

    def _rodar(self, d):
        from unittest import mock
        prompts = []

        def falso(pasta, modelo, p, arquivo, timeout=None, tentativas=2, effort=None):
            prompts.append(p)
            texto = 'CRITERIO C1: PASS\nCRITERIO C2: PASS\nVEREDICTO: APROVADO\n'
            with open(os.path.join(pasta, arquivo), 'w', encoding='utf-8', newline='\n') as f:
                f.write(texto)
            return texto, {}, 'ok'

        with mock.patch.dict(os.environ, {'OCOMBO_MODO': '0'}), \
                mock.patch.object(dupla.juiz, 'chamar_juiz', falso), \
                mock.patch.object(dupla.juiz, 'registrar_custo', lambda *a, **k: ''), \
                mock.patch.object(dupla, '_ledger_dupla', lambda *a, **k: None):
            rc = dupla.rodar(d, self.B)
        return rc, prompts[0]

    def test_r2_julga_os_fail_do_proprio_b(self):
        d = self._instancia()
        try:
            rc, p = self._rodar(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(rc, 0)
        self.assertNotIn('julgue so a regressao', p)
        self.assertIn('C1', p.split('(ainda nao julgados):')[1].split('—')[0])
        self.assertIn('historico/veredicto.%s.r1.md' % self.B, p)

    def test_guarda_o_proprio_veredicto_no_historico(self):
        d = self._instancia()
        try:
            self._rodar(d)
            existe = os.path.exists(os.path.join(d, 'historico', 'veredicto.%s.r2.md' % self.B))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertTrue(existe)

    def test_sem_veredicto_anterior_do_b_julga_o_que_o_a_deixou_pendente(self):
        d = self._instancia(b_anterior=False)
        try:
            rc, p = self._rodar(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertIn('C2', p.split('(ainda nao julgados):')[1].split('—')[0])


if __name__ == '__main__':
    unittest.main()
