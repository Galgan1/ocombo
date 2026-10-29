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
        c = juiz.custo(resp, rodada=2, modelo='claude-sonnet-5-5')
        self.assertEqual(c['rodada'], 2)
        self.assertEqual(c['input'], 120)
        self.assertEqual(c['cache_read'], 9000)
        self.assertAlmostEqual(c['usd'], 0.0123)
        self.assertEqual(c['segundos'], 4.5)
        linha = juiz.linha_custo(c)
        self.assertIn('r2', linha)
        self.assertIn('claude-sonnet-5-5', linha)
        self.assertIn('0.0123', linha)
        self.assertNotIn('effort=', linha)   # sem effort, a linha e a de sempre (parser antigo continua lendo)

    def test_linha_custo_com_effort(self):
        resp = {'total_cost_usd': 0.5, 'duration_ms': 1000, 'num_turns': 2, 'usage': {'input_tokens': 1, 'output_tokens': 2}}
        linha = juiz.linha_custo(juiz.custo(resp, rodada=1, modelo='m', effort='high'))
        self.assertTrue(linha.endswith(' effort=high'), linha)
        self.assertIn('turnos=2', linha)

    def test_resolver_effort_explicito_vence_modo(self):
        import modos
        p = modos.PERFIS[6]                    # juiz_effort high
        self.assertEqual(juiz.resolver_effort(None, p), 'high')
        self.assertEqual(juiz.resolver_effort('low', p), 'low')
        self.assertIsNone(juiz.resolver_effort(None, modos.PERFIS[0]))
        with self.assertRaises(ValueError):
            juiz.resolver_effort('banana', p)

    def test_escada_ativa_pelo_plano_ou_ambiente(self):
        d = tempfile.mkdtemp()
        amb = os.environ.pop('OCOMBO_ESCADA', None)
        try:
            self.assertFalse(juiz.escada_ativa(d))
            with open(os.path.join(d, 'solucao.txt'), 'w', encoding='utf-8') as f:
                f.write('=== ESTADO ===\nModo deste ciclo: 2 (atento) | juiz x | teto 5 rodadas | dupla nao | paralelo 2\n')
            self.assertFalse(juiz.escada_ativa(d))
            with open(os.path.join(d, 'solucao.txt'), 'w', encoding='utf-8') as f:
                f.write('=== ESTADO ===\nModo deste ciclo: 2 (atento) | juiz x | teto 5 rodadas | dupla nao | paralelo 2 | escada: sim\n')
            self.assertTrue(juiz.escada_ativa(d))
            os.environ['OCOMBO_ESCADA'] = '1'
            self.assertTrue(juiz.escada_ativa(tempfile.mkdtemp()))
        finally:
            os.environ.pop('OCOMBO_ESCADA', None)
            if amb is not None:
                os.environ['OCOMBO_ESCADA'] = amb

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

    def test_aprovado_solto_em_prosa_nunca_aprova(self):
        # Incidente 28/09/2026 (ciclo de um site): o veredicto reprovou C0, mas citava em prosa
        # "apos o APROVADO r5 de la" (outra instancia) e o parser carimbou APROVADO. Sem linha canonica,
        # um FAIL de criterio manda AJUSTE e um APROVADO solto nunca aprova.
        texto = 'CRITERIO C0: FAIL - ...\nremedidos apos o APROVADO r5 de la\nCRITERIO C1: N/A\n'
        self.assertEqual(juiz.veredicto(texto), 'AJUSTE')
        self.assertEqual(juiz.veredicto('tudo lindo, APROVADO pelo dono em outra rodada'), 'INDEFINIDO')
        self.assertEqual(juiz.veredicto('CRITERIO C0: PASS\nCRITERIO C1: PASS\n'), 'INDEFINIDO')


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

    def test_rodada_sem_juiz_anterior_vira_leitura_inteira(self):
        # 16/10/2026 (revisao-de-uma-skill): r1 parou na prova, r2 na triagem; a r3 recebeu "julgue so a
        # regressao" sem nenhum veredicto anterior e APROVOU em 20 s sem ler a solucao. Sem veredicto
        # julgado antes (arquivo ausente ou sem linhas CRITERIO), a rodada e de leitura inteira.
        self.assertEqual(juiz.rodada_do_prompt(3, None), 1)
        self.assertEqual(juiz.rodada_do_prompt(3, 'VEREDICTO: AJUSTE\n\nA TRIAGEM reprovou\n'), 1)
        self.assertEqual(juiz.rodada_do_prompt(3, 'CRITERIO C0: PASS\nCRITERIO C1: FAIL\nVEREDICTO: AJUSTE\n'), 3)
        self.assertEqual(juiz.rodada_do_prompt(1, None), 1)
        self.assertIn('por inteiro', juiz.prompt(juiz.rodada_do_prompt(3, None), [], True))

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


class TestCriterioNovo(unittest.TestCase):
    """17/10/2026 (ciclo de um video, rodada 2): critério que entra na RUBRICA no meio do ciclo (emenda do dono)
    nunca era julgado na rodada por diff, porque só o FAIL e o N/A do veredicto anterior voltavam ao juiz."""
    SOL = ('=== ESTADO ===\nx\n=== RUBRICA (binaria) ===\nAtalhos: C1 e C2\n'
           'C0. CONFORMIDADE [LEITURA]: a\nC7. LEGIVEL [MEDIDO]: b\nC7b. DECISAO 1b [MEDIDO]: c\n'
           'C13b. DECISAO 2b [MEDIDO]: d\nC26. REGRESSAO [MEDIDO]: e\n\n=== SOLUCAO ===\nC99. nao e da rubrica\n')

    def test_criterios_da_rubrica(self):
        self.assertEqual(juiz.criterios_da_rubrica(self.SOL), ['C0', 'C7', 'C7b', 'C13b', 'C26'])

    def test_criterio_nunca_julgado_entra_nos_pendentes(self):
        ant = 'CRITERIO C0: PASS\nCRITERIO C7: PASS\nCRITERIO C26: FAIL\nVEREDICTO: AJUSTE\n'
        self.assertEqual(juiz.pendentes_com_novos(ant, self.SOL), ['C26', 'C7b', 'C13b'])

    def test_sem_veredicto_anterior_a_lista_fica_vazia(self):
        self.assertEqual(juiz.pendentes_com_novos(None, self.SOL), [])

    def test_julgado_em_rodada_mais_antiga_nao_e_novo(self):
        # rodada por diff: o veredicto anterior so imprime o que julgou; o que uma rodada mais antiga julgou nao e novo
        r2 = 'CRITERIO C0: PASS\nCRITERIO C7: PASS\nCRITERIO C26: PASS\nVEREDICTO: AJUSTE\n'
        r3 = 'CRITERIO C7b: PASS\nCRITERIO C13b: N/A\nVEREDICTO: APROVADO\n'
        self.assertEqual(juiz.pendentes_com_novos(r3, self.SOL, historico=[r2, r3]), ['C13b'])


class TestBackendAgy(unittest.TestCase):
    """v15 (23/10/2026, antigravity-juiz): o Antigravity CLI oficial (`agy`) e o juiz; prefixo agy: no id do modelo.
    Nenhum teste chama agy nem claude: a execucao e injetada (executar=...)."""
    HASH_LINHA_CLAUDE = 'e712ee155ae66891472c7f27f89f15520aa3040c21b23656d2b953315c070e9b'   # medido antes da v15

    def test_backend_pelo_prefixo(self):
        self.assertEqual(juiz.backend_de('agy:gemini-4-argon-high'), 'agy')
        self.assertEqual(juiz.backend_de('claude-sonnet-5-5'), 'claude')
        self.assertEqual(juiz.backend_de('claude-haiku-4-5-20251001'), 'claude')

    def test_linha_claude_byte_a_byte(self):
        import hashlib
        a = juiz.argumentos_claude('claude-sonnet-5-5', None, executavel='claude')
        self.assertEqual(hashlib.sha256(' '.join(a).encode()).hexdigest(), self.HASH_LINHA_CLAUDE)

    def test_juiz_claude_por_ambiente(self):
        import modos
        amb = os.environ.pop('OCOMBO_JUIZ_CLAUDE', None)
        try:
            self.assertEqual(juiz.resolver_modelo(None, modos.PERFIS[0]), juiz.MODELO_CLAUDE)   # v16: Gemini fora
            os.environ['OCOMBO_JUIZ_CLAUDE'] = '1'
            self.assertEqual(juiz.resolver_modelo(None, modos.PERFIS[0]), juiz.MODELO_CLAUDE)
            self.assertEqual(juiz.resolver_modelo('claude-opus-5-5', modos.PERFIS[0]), 'claude-opus-5-5')
        finally:
            os.environ.pop('OCOMBO_JUIZ_CLAUDE', None)
            if amb is not None:
                os.environ['OCOMBO_JUIZ_CLAUDE'] = amb

    def test_linha_agy_sem_skip_permissions_nem_effort(self):
        a = juiz.argumentos_agy('gemini-4-argon-high', 'julgue', 900, add_dirs=[r'C:\x\repo'], agente='juiz', executavel='agy')
        self.assertEqual(a[:3], ['agy', '-p', 'julgue'])
        for flag in ('--disable-slash-commands', '--output-format', 'json', '--print-timeout', '900s', '--add-dir', r'C:\x\repo', '--agent', 'juiz'):
            self.assertIn(flag, a)
        self.assertNotIn('--dangerously-skip-permissions', a)
        self.assertNotIn('--effort', a)
        self.assertNotIn('--mode', a)   # medido 23/10: "--mode plan has no effect while slash command expansion is disabled"
        self.assertEqual(a[a.index('--model') + 1], 'gemini-4-argon-high')

    def test_sufixo_de_effort(self):
        self.assertEqual(juiz.modelo_agy('gemini-4-argon', 'low'), 'gemini-4-argon-low')
        self.assertEqual(juiz.modelo_agy('gemini-4-argon', 'medium'), 'gemini-4-argon-medium')
        for e in ('high', 'xhigh', 'max', None):
            self.assertEqual(juiz.modelo_agy('gemini-4-argon', e), 'gemini-4-argon-high')
        self.assertEqual(juiz.modelo_agy('gemini-4-argon-high', 'low'), 'gemini-4-argon-low')

    def test_fila_segue_a_partir_do_pedido_com_o_mesmo_sufixo(self):
        self.assertEqual(juiz.fila_agy('gemini-4-argon-high'), ['gemini-4-argon-high', 'gemini-3.8-flash-high', 'claude-sonnet-5-5-high'])
        self.assertEqual(juiz.fila_agy('gemini-3.8-flash-low'), ['gemini-3.8-flash-low', 'claude-sonnet-5-5-low'])
        self.assertEqual(juiz.fila_agy('gpt-oss-120b-medium'), ['gpt-oss-120b-medium'])

    def test_raizes_de_leitura_deduplica_e_recusa(self):
        d = tempfile.mkdtemp()
        try:
            repo = os.path.join(d, 'repo')
            os.makedirs(os.path.join(repo, '.git'))
            os.makedirs(os.path.join(repo, 'tests'))
            open(os.path.join(repo, 'a.py'), 'w').close()
            open(os.path.join(repo, 'tests', 'b.py'), 'w').close()
            os.makedirs(os.path.join(d, 'solto'))
            open(os.path.join(d, 'solto', 'x.txt'), 'w').close()
            texto = ('cita %s e %s e %s e %s e %s e C:\\ e %s e %s e %s' % (os.path.join(repo, 'a.py'), os.path.join(repo, 'tests', 'b.py'),
                     os.path.join(repo, 'tests', 'b.py').replace('\\', '/'), os.path.join(d, '.secrets', 'k.txt'),
                     os.path.expanduser('~'), os.path.join(d, 'solto', 'x.txt'), os.path.join(d, 'nao-existe', 'y.txt'),
                     os.path.join(os.path.expanduser('~'), 'Documents')))
            raizes = juiz.raizes_de_leitura(texto, home=os.path.expanduser('~'))
            # repo pela raiz git; 'solto' pela pasta; .secrets, a home, C:\, Documents inteiro e o caminho inexistente ficam de fora
            self.assertEqual([r.lower() for r in raizes], sorted({repo.lower(), os.path.join(d, 'solto').lower()}))
            # home FALSA = d: dados do app inteiros nunca; subpasta citada do scratch sim; filha de raiz liberada some
            for sub in (('.gemini', 'antigravity', 'conversations'), ('.gemini', 'antigravity', 'scratch', 'bib'), ('.gemini', 'config')):
                os.makedirs(os.path.join(d, *sub), exist_ok=True)
                open(os.path.join(d, *sub, 'f.txt'), 'w').close()
            falsa = ('cita %s e %s e %s e %s' % (os.path.join(d, '.gemini', 'antigravity', 'venci.bat'), os.path.join(d, '.gemini', 'antigravity', 'conversations', 'f.txt'),
                                                 os.path.join(d, '.gemini', 'antigravity', 'scratch', 'bib', 'f.txt'), os.path.join(d, '.gemini', 'config', 'f.txt')))
            self.assertEqual([r.lower() for r in juiz.raizes_de_leitura(falsa, home=d)],
                             sorted({os.path.join(d, '.gemini', 'antigravity', 'scratch', 'bib').lower(), os.path.join(d, '.gemini', 'config').lower()}))
            self.assertEqual([r.lower() for r in juiz.raizes_de_leitura('%s e %s' % (repo, os.path.join(repo, 'tests', 'b.py')), home=d)], [repo.lower()])
            # grafias relativas a home (~/, %USERPROFILE%\, $env:USERPROFILE\) tambem liberam a pasta citada
            rel = os.path.relpath(os.path.join(d, 'solto', 'x.txt'), os.path.expanduser('~'))
            if not rel.startswith('..'):
                for forma in ('~/' + rel.replace('\\', '/'), '%USERPROFILE%\\' + rel, '$env:USERPROFILE\\' + rel):
                    self.assertEqual([r.lower() for r in juiz.raizes_de_leitura('veja ' + forma, home=os.path.expanduser('~'))],
                                     [os.path.join(d, 'solto').lower()], forma)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_copia_so_leitura_do_que_fica_fora_das_raizes(self):
        # 23/10/2026 r3: view_file de ~/.gemini/GEMINI.md auto-negado (a pasta .gemini inteira nunca e liberada) matou a rodada
        d = tempfile.mkdtemp()
        try:
            inst = os.path.join(d, 'inst')
            os.makedirs(os.path.join(d, '.gemini', '.secrets'))
            os.makedirs(inst)
            with open(os.path.join(d, '.gemini', 'GEMINI.md'), 'w') as f:
                f.write('regra\n')
            with open(os.path.join(d, '.gemini', '.secrets', 'k.txt'), 'w') as f:
                f.write('segredo\n')
            with open(os.path.join(d, '.claude.json'), 'w') as f:
                f.write('{"oauth": "x"}\n')
            texto = 'cita %s e %s e %s e %s' % (os.path.join(d, '.gemini', 'GEMINI.md'), os.path.join(d, '.gemini', '.secrets', 'k.txt'),
                                               os.path.join(inst, 'solucao.txt'), os.path.join(d, '.claude.json'))
            raizes = juiz.raizes_de_leitura(texto, home=d)
            self.assertEqual([r.lower() for r in raizes], [inst.lower()])   # .gemini inteira nao vira raiz; a instancia sim
            copias = juiz.copias_de_leitura(texto, inst, raizes, home=d)   # .claude.json (solto na home) nunca e copiado
            self.assertEqual([os.path.basename(c) for _, c in copias], ['GEMINI.md'])
            self.assertEqual(open(copias[0][1]).read(), 'regra\n')
            self.assertFalse(os.path.exists(os.path.join(inst, 'historico', 'leitura', 'k.txt')))   # segredo nunca
            # arquivo dentro de raiz liberada nao e copiado
            self.assertEqual(juiz.copias_de_leitura(texto, inst, [os.path.join(d, '.gemini')], home=d), [])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_copia_so_leitura_purga_resto_antigo_e_recusa_conteudo_com_segredo(self):
        # fecho de 23/10/2026 (Fable): historico/leitura/.claude.json (chave de API em texto puro) ficou na instancia
        # de uma rodada antiga, ao alcance do juiz do Google, porque a copia so filtrava pelo CAMINHO e nunca limpava a pasta
        d = tempfile.mkdtemp()
        try:
            inst = os.path.join(d, 'inst')
            os.makedirs(os.path.join(inst, 'historico', 'leitura'))
            os.makedirs(os.path.join(d, '.gemini'))
            with open(os.path.join(inst, 'historico', 'leitura', '.claude.json'), 'w') as f:   # resto de rodada antiga
                f.write('{"ELEVENLABS_API_KEY": "sk_01' + '23456789abcdef0123456789abcdef"}\n')
            with open(os.path.join(d, '.gemini', 'GEMINI.md'), 'w') as f:
                f.write('regra\n')
            with open(os.path.join(d, '.gemini', 'config.json'), 'w') as f:                   # conteudo com segredo
                f.write('{"mcp": {"env": {"API_KEY": "AIzaS' + 'yA1234567890abcdefghijklmnopqrstuvw"}}}\n')
            texto = 'cita %s e %s' % (os.path.join(d, '.gemini', 'GEMINI.md'), os.path.join(d, '.gemini', 'config.json'))
            copias = juiz.copias_de_leitura(texto, inst, [], home=d)
            self.assertEqual([os.path.basename(c) for _, c in copias], ['GEMINI.md'])
            self.assertEqual(sorted(os.listdir(os.path.join(inst, 'historico', 'leitura'))), ['GEMINI.md'])   # resto purgado
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_segredos_na_instancia_pre_voo(self):
        # (c) do fecho: antes de montar o --add-dir o juiz varre a instancia por VALOR com cara de segredo (nao por palavra:
        # 'api_key' em prosa de veredicto nao conta); achou = INDEFINIDO 'segredo', o juiz nao e chamado
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, 'evidencias'))
            with open(os.path.join(d, 'veredicto.md'), 'w') as f:
                f.write('C1: PASS. O texto fala de api_key e token em prosa, sem valor.\n')
            self.assertEqual(juiz.segredos_na_instancia(d), [])
            # segredo em evidencias/ (historico/leitura e purgado pela copia; o pre-voo cobre o RESTO da instancia)
            with open(os.path.join(d, 'evidencias', 'x.json'), 'w') as f:
                f.write('{"ELEVENLABS_API_KEY": "sk_01' + '23456789abcdef0123456789abcdef"}\n')
            achados = juiz.segredos_na_instancia(d)
            self.assertEqual([(os.path.basename(a), l) for a, l, _ in achados], [('x.json', 1)])
            self.assertNotIn('0123456789abcdef', repr(achados))   # o achado nunca carrega o valor
            # chamar_agy para antes de executar qualquer coisa
            chamadas = []
            texto, resp, status = juiz.chamar_agy(d, 'agy:gemini-3.8-flash-high', 'prompt', 'veredicto.md',
                                                  executar=lambda *a, **k: chamadas.append(a) or {'returncode': 0, 'stdout': '', 'stderr': ''},
                                                  cota_cache=os.path.join(d, 'cota.json'))
            self.assertEqual(chamadas, [])
            self.assertEqual(status, 'segredo')
            self.assertIn('VEREDICTO: INDEFINIDO', texto)
            self.assertIn('x.json', texto)
            self.assertNotIn('0123456789abcdef', texto)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_prazo_de_reset(self):
        from datetime import datetime
        agora = datetime(2026, 10, 23, 10, 0, 0)
        ate = juiz.prazo_de_reset('Individual quota reached. Resets in 126h14m33s.', agora)
        self.assertEqual(ate, datetime(2026, 10, 28, 16, 14, 33))
        self.assertIsNone(juiz.prazo_de_reset('sem prazo', agora))

    def _instancia(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'solucao.txt'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('=== ESTADO ===\nx\n=== RUBRICA ===\nC0. a\n=== SOLUCAO ===\ncita C:\\nada\\daqui.txt\n')
        os.makedirs(os.path.join(d, 'historico'))
        return d

    def _executar_com(self, respostas):
        """Fabrica um executar(args, cwd, timeout) que devolve as respostas em ordem e anota os modelos pedidos."""
        chamados = []
        import subprocess

        def executar(args, cwd, timeout):
            chamados.append(args[args.index('--model') + 1])
            r = respostas.pop(0)
            if r == 'timeout':
                raise subprocess.TimeoutExpired(args, timeout)
            return r
        return executar, chamados

    def test_fila_pula_esgotado_e_guarda_a_hora(self):
        d = self._instancia()
        cota = os.path.join(d, 'cota.json')
        import json
        esgotado = (3, json.dumps({'status': 'ERROR', 'response': '', 'error': 'Individual quota reached. Resets in 126h14m33s.', 'usage': {}}), 'AGY_ERROR: RESOURCE_EXHAUSTED (code 429)')
        ok = (0, json.dumps({'status': 'SUCCESS', 'response': 'CRITERIO C0: PASS\nVEREDICTO: APROVADO\n', 'duration_seconds': 9.5, 'num_turns': 1,
                             'usage': {'input_tokens': 100, 'output_tokens': 20, 'thinking_tokens': 5, 'cache_read_tokens': 0}}), '')
        executar, chamados = self._executar_com([esgotado, ok])
        texto, resp, status = juiz.chamar_juiz(d, 'agy:gemini-4-argon-high', 'julgue', 'veredicto.md', timeout=10, executar=executar, cota_cache=cota)
        self.assertEqual(status, 'ok')
        self.assertEqual(chamados, ['gemini-4-argon-high', 'gemini-3.8-flash-high'])
        self.assertIn('VEREDICTO: APROVADO', texto)
        self.assertEqual(juiz.veredicto(texto), 'APROVADO')
        self.assertEqual(resp['_ocombo']['modelo'], 'gemini-3.8-flash-high')
        self.assertEqual(resp['_ocombo']['fila'], 'gemini-4-argon-high=esgotado,gemini-3.8-flash-high=ok')
        guardado = json.load(open(cota, encoding='utf-8'))
        self.assertIn('gemini-4-argon-high', guardado)
        # segunda chamada: o argon esta esgotado na cache -> nao gasta chamada nele
        executar2, chamados2 = self._executar_com([ok])
        juiz.chamar_juiz(d, 'agy:gemini-4-argon-high', 'julgue', 'veredicto.md', timeout=10, executar=executar2, cota_cache=cota)
        self.assertEqual(chamados2, ['gemini-3.8-flash-high'])
        shutil.rmtree(d, ignore_errors=True)

    def test_fila_toda_esgotada_e_indefinido_cota_sem_claude(self):
        import json
        d = self._instancia()
        esg = (3, json.dumps({'status': 'ERROR', 'response': '', 'error': 'quota reached. Resets in 1h0m0s.', 'usage': {}}), '')
        executar, chamados = self._executar_com([esg, esg, esg])
        texto, resp, status = juiz.chamar_juiz(d, 'agy:gemini-4-argon-high', 'julgue', 'veredicto.md', timeout=10, executar=executar,
                                               cota_cache=os.path.join(d, 'cota.json'))
        self.assertEqual(status, 'cota')
        self.assertEqual(juiz.veredicto(texto), 'INDEFINIDO')
        self.assertIn('cota', texto.lower())
        self.assertEqual(len(chamados), 3)
        self.assertTrue(all('claude' in c or 'gemini' in c for c in chamados))   # nunca cai no claude -p local
        self.assertTrue(open(os.path.join(d, 'veredicto.md'), encoding='utf-8').read().startswith('VEREDICTO: INDEFINIDO'))
        shutil.rmtree(d, ignore_errors=True)

    def test_resposta_vazia_e_indefinido_permissao(self):
        import json
        d = self._instancia()
        vazio = (0, json.dumps({'status': 'SUCCESS', 'response': '', 'usage': {}}), 'jetski: no output produced - a tool required the "read_file" permission')
        executar, _ = self._executar_com([vazio])
        texto, resp, status = juiz.chamar_juiz(d, 'agy:gemini-3.8-flash-high', 'julgue', 'veredicto.md', timeout=10, executar=executar,
                                               cota_cache=os.path.join(d, 'cota.json'))
        self.assertEqual(status, 'permissao')
        self.assertEqual(juiz.veredicto(texto), 'INDEFINIDO')
        self.assertIn('read_file', texto)
        shutil.rmtree(d, ignore_errors=True)

    def test_timeout_duas_vezes_e_indefinido(self):
        d = self._instancia()
        executar, chamados = self._executar_com(['timeout', 'timeout'])
        texto, resp, status = juiz.chamar_juiz(d, 'agy:gemini-3.8-flash-high', 'julgue', 'veredicto.md', timeout=10, executar=executar,
                                               cota_cache=os.path.join(d, 'cota.json'))
        self.assertEqual(status, 'timeout')
        self.assertEqual(juiz.veredicto(texto), 'INDEFINIDO')
        self.assertEqual(len(chamados), 2)
        shutil.rmtree(d, ignore_errors=True)

    def test_prompt_grande_vai_a_arquivo(self):
        import json
        d = self._instancia()
        ok = (0, json.dumps({'status': 'SUCCESS', 'response': 'VEREDICTO: AJUSTE\n', 'usage': {}}), '')
        capturado = []

        def executar(args, cwd, timeout):
            capturado.append(args[args.index('-p') + 1])
            return ok
        juiz.chamar_juiz(d, 'agy:gemini-3.8-flash-high', 'x' * 24000, 'veredicto.md', timeout=10, executar=executar, cota_cache=os.path.join(d, 'cota.json'))
        self.assertLess(len(capturado[0]), 400)
        self.assertIn('historico', capturado[0])
        arquivos = os.listdir(os.path.join(d, 'historico'))
        self.assertTrue(any(a.startswith('prompt.r') for a in arquivos), arquivos)
        shutil.rmtree(d, ignore_errors=True)

    def test_dados_pessoais_no_estado_forca_claude(self):
        d = tempfile.mkdtemp()
        sol = os.path.join(d, 'solucao.txt')
        with open(sol, 'w', encoding='utf-8', newline='\n') as f:
            f.write('=== ESTADO ===\nDados: esta instancia tem CPF e extrato de cliente: dados pessoais\n=== SOLUCAO ===\nfala de dados pessoais\n')
        self.assertEqual(juiz.backend_forcado(d), 'claude')
        with open(sol, 'w', encoding='utf-8', newline='\n') as f:
            f.write('=== ESTADO ===\n  Dados pessoais ao fim de linha recuada nao conta\nDados : nao tem dado de cliente (pode ir ao agy). D2 = linha que termina em pessoais, so no ESTADO.\n=== SOLUCAO ===\nDados ... pessoais\n')
        self.assertIsNone(juiz.backend_forcado(d))
        import modos
        with open(sol, 'w', encoding='utf-8', newline='\n') as f:
            f.write('=== ESTADO ===\nDados: CPF de cliente: pessoais\n=== SOLUCAO ===\n')
        self.assertEqual(juiz.resolver_modelo(None, modos.PERFIS[0], pasta=d), juiz.MODELO_CLAUDE)
        real = os.path.join(os.path.expanduser('~'), 'antigravity-juiz', 'ocombo')
        if os.path.exists(os.path.join(real, 'solucao.txt')):
            self.assertIsNone(juiz.backend_forcado(real))   # ESTE solucao.txt cita a frase em prosa e NAO pode disparar
        shutil.rmtree(d, ignore_errors=True)

    def test_tripwire_ve_arquivo_novo_e_alterado(self):
        d = self._instancia()
        antes = juiz.tripwire_retrato(d)
        self.assertIn('solucao.txt', antes)
        with open(os.path.join(d, 'veredicto.md'), 'w') as f:
            f.write('ignorado')
        with open(os.path.join(d, 'custo.log'), 'w') as f:
            f.write('ignorado')
        self.assertEqual(juiz.tripwire_violacoes(antes, juiz.tripwire_retrato(d)), [])
        with open(os.path.join(d, 'novo.txt'), 'w') as f:
            f.write('x')
        with open(os.path.join(d, 'solucao.txt'), 'a') as f:
            f.write('mexido\n')
        v = juiz.tripwire_violacoes(antes, juiz.tripwire_retrato(d))
        self.assertEqual(sorted(v), ['novo.txt', 'solucao.txt'])
        shutil.rmtree(d, ignore_errors=True)

    def test_tripwire_na_chamada_vira_indefinido_violacao(self):
        import json
        d = self._instancia()
        ok = (0, json.dumps({'status': 'SUCCESS', 'response': 'VEREDICTO: APROVADO\n', 'usage': {}}), '')

        def executar(args, cwd, timeout):
            with open(os.path.join(d, 'criado-pelo-juiz.txt'), 'w') as f:
                f.write('violacao')
            return ok
        texto, resp, status = juiz.chamar_juiz(d, 'agy:gemini-3.8-flash-high', 'julgue', 'veredicto.md', timeout=10, executar=executar, cota_cache=os.path.join(d, 'cota.json'))
        self.assertEqual(status, 'violacao')
        self.assertEqual(juiz.veredicto(texto), 'INDEFINIDO')
        self.assertIn('criado-pelo-juiz.txt', texto)
        self.assertEqual(resp['_ocombo']['tripwire'], 1)
        shutil.rmtree(d, ignore_errors=True)

    def test_custo_do_agy_em_tokens_sem_usd(self):
        resp = {'status': 'SUCCESS', 'duration_seconds': 17.4, 'num_turns': 1,
                'usage': {'input_tokens': 32059, 'output_tokens': 1076, 'thinking_tokens': 1075, 'cache_read_tokens': 0, 'total_tokens': 33135},
                '_ocombo': {'modelo': 'gemini-3.8-flash-high', 'fila': 'gemini-4-argon-high=esgotado,gemini-3.8-flash-high=ok', 'tripwire': 0}}
        c = juiz.custo(resp, 1, 'agy:gemini-4-argon-high')
        self.assertIsNone(c['usd'])
        self.assertEqual(c['input'], 32059)
        self.assertEqual(c['segundos'], 17.4)
        linha = juiz.linha_custo(c)
        for trecho in ('r1', 'agy:gemini-3.8-flash-high', 'in=32059', 'out=1076', 'thinking=1075', 'cache_read=0', 'usd=n/d',
                       'fila=gemini-4-argon-high=esgotado,gemini-3.8-flash-high=ok', 'tripwire: 0 violacoes'):
            self.assertIn(trecho, linha)
        self.assertNotIn('sem usage', linha)

    def test_prompt_do_agy_nao_manda_gravar(self):
        p = juiz.prompt(1, [], False, backend='agy')
        self.assertNotIn('Escreva veredicto.md', p)
        self.assertIn('VEREDICTO: APROVADO', p)
        self.assertIn('CRITERIO <id>: PASS', p)
        self.assertIn('Escreva veredicto.md', juiz.prompt(1, [], False))   # claude: byte a byte como antes


if __name__ == '__main__':
    unittest.main()
