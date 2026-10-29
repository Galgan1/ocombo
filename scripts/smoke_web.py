# -*- coding: utf-8 -*-
"""Smoke de navegador do ocombo (rubrica site C4): abre a URL no Chromium headless via Playwright.

Uso:  python smoke_web.py <url> [--texto "Entrar"] [--seletor css] [--saida arquivo.txt]
                             [--spec caminho/do/spec.js]
  exit 0 = pagina abriu sem erro de JS, sem 5xx e com o esperado; 1 = falhou; 2 = Playwright ausente.

Onde o Playwright vem (primeiro que existir): ./node_modules/@playwright/test (o repo atual) ->
$OCOMBO_NODE_TOOLS/node_modules/@playwright/test. Instalar uma vez na pasta escolhida:
  npm i -D @playwright/test && npx playwright install chromium
`--spec` (09/09/2026): pagina ATRAS DE LOGIN precisa de passos proprios (entrar, esperar a tela).
Desde 10/09/2026 a TELA DE LOGIN em si ja passa no spec padrao: o 401 da checagem de sessao e um relato do
navegador, nao erro de JS, e `assets/playwright/filtro.js` o separa (SMOKE_IGNORAR_STATUS, padrao 401,403;
5xx nunca se tolera). O proprio spec padrao ja mandava "copie este arquivo
para o repo e acrescente passos"; `--spec` faz esse spec do repo rodar POR AQUI, para o exit code sair
desta ferramenta e a evidencia ser a mesma de sempre. O arquivo e copiado como `smoke.spec.js` no destino
(o testMatch da config nao muda). Senha SEMPRE por variavel de ambiente, nunca no argumento.

O spec e a config (assets/playwright/) sao COPIADOS para <pasta>/ocombo-smoke/ antes de rodar, porque o
`require('@playwright/test')` resolve relativo ao arquivo de config (medido em 06/09/2026: rodar a config
de dentro da skill da MODULE_NOT_FOUND). Relatorio: saida do runner + resumo do JSON + EXIT= no fim.
"""
import json
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(AQUI, '..', 'assets', 'playwright')


def pasta_playwright():
    """Pasta com node_modules/@playwright/test, ou None."""
    for base in [os.getcwd(), os.environ.get('OCOMBO_NODE_TOOLS') or '']:
        if base and os.path.isdir(os.path.join(base, 'node_modules', '@playwright', 'test')):
            # realpath devolve a CAIXA real do caminho no Windows: com "c--users-x" x "C--Users-X"
            # o Node carrega @playwright/test duas vezes e o runner acusa "two different versions" (06/09/2026)
            return os.path.realpath(base)
    return None


def resumo(relatorio_json):
    """JSON do reporter do Playwright -> (passaram, falharam, [mensagens de erro])."""
    try:
        d = json.loads(relatorio_json or '{}')
    except ValueError:
        return 0, 0, ['relatorio ilegivel']
    erros = []
    contagem = {'p': 0, 'f': 0}

    def andar2(suite):
        for spec in suite.get('specs', []):
            for t in spec.get('tests', []):
                for r in t.get('results', []):
                    st = r.get('status')
                    if st == 'passed':
                        contagem['p'] += 1
                    elif st in ('failed', 'timedOut', 'interrupted'):
                        contagem['f'] += 1
                        e = r.get('error') or {}
                        erros.append((e.get('message') or 'sem mensagem').splitlines()[0][:300])
        for s in suite.get('suites', []):
            andar2(s)

    for s in d.get('suites', []):
        andar2(s)
    return contagem['p'], contagem['f'], erros


def main(argv):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if not argv or not argv[0].startswith(('http', 'data:')):
        print(__doc__)
        return 2
    url = argv[0]
    texto = seletor = saida = spec = None
    i = 1
    while i < len(argv):
        if argv[i] == '--texto':
            texto = argv[i + 1]
            i += 2
        elif argv[i] == '--seletor':
            seletor = argv[i + 1]
            i += 2
        elif argv[i] == '--saida':
            saida = argv[i + 1]
            i += 2
        elif argv[i] == '--spec':
            spec = argv[i + 1]
            i += 2
        else:
            i += 1
    base = pasta_playwright()
    linhas = ['[smoke_web] url=' + url]
    if not base:
        linhas.append('Playwright AUSENTE: npm i -D @playwright/test && npx playwright install chromium '
                      '(no repo ou em OCOMBO_NODE_TOOLS)')
        texto_fim = '\n'.join(linhas + ['EXIT=2'])
        print(texto_fim)
        if saida:
            open(saida, 'w', encoding='utf-8').write(texto_fim + '\n')
        return 2
    alvo = os.path.join(base, 'ocombo-smoke')
    os.makedirs(alvo, exist_ok=True)
    shutil.copyfile(os.path.join(ASSETS, 'playwright.config.js'), os.path.join(alvo, 'playwright.config.js'))
    # filtro.js viaja junto: o spec (o padrao e o do repo) faz require('./filtro.js') (10/09/2026)
    shutil.copyfile(os.path.join(ASSETS, 'filtro.js'), os.path.join(alvo, 'filtro.js'))
    if spec:
        if not os.path.isfile(spec):
            linhas.append('spec inexistente: ' + spec)
            texto_fim = chr(10).join(linhas + ['EXIT=2'])
            print(texto_fim)
            if saida:
                open(saida, 'w', encoding='utf-8').write(texto_fim + chr(10))
            return 2
        linhas.append('[spec do repo] ' + os.path.abspath(spec))
    shutil.copyfile(spec or os.path.join(ASSETS, 'smoke.spec.js'), os.path.join(alvo, 'smoke.spec.js'))
    rel_json = os.path.join(alvo, 'relatorio.json')
    env = dict(os.environ)
    env['SMOKE_URL'] = url
    env['PW_JSON'] = rel_json
    if texto:
        env['SMOKE_TEXTO'] = texto
    if seletor:
        env['SMOKE_SELETOR'] = seletor
    cmd = ['npx', 'playwright', 'test', '--config', os.path.join(alvo, 'playwright.config.js')]
    r = subprocess.run(cmd, cwd=base, env=env, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', shell=(os.name == 'nt'))
    linhas.append((r.stdout or '').strip()[-2500:])
    if r.stderr.strip():
        linhas.append('[stderr] ' + r.stderr.strip()[-800:])
    if os.path.exists(rel_json):
        p, f, erros = resumo(open(rel_json, encoding='utf-8').read())
        linhas.append('resumo: %d passou, %d falhou' % (p, f))
        linhas += ['  ' + e for e in erros]
        exit_code = 0 if (f == 0 and p > 0) else 1
    else:
        linhas.append('sem relatorio JSON (runner exit %d)' % r.returncode)
        exit_code = 1 if r.returncode else 2
    linhas.append('EXIT=%d' % exit_code)
    texto_fim = '\n'.join(linhas)
    print(texto_fim)
    if saida:
        with open(saida, 'w', encoding='utf-8') as f:
            f.write(texto_fim + '\n')
    return exit_code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
