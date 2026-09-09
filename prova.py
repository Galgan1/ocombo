# -*- coding: utf-8 -*-
"""Portao unico da skill ocombo (Akita: verde = exit 0).

Checa a forma da skill (SKILL.md magro, secoes das 5 melhorias, fontes auditadas, LF,
sem segredo, arquivos referenciados existem) e roda os testes unitarios de scripts/juiz.py
sem chamar `claude`. Uso: python prova.py  (exit 0 = verde)
"""
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(AQUI, 'SKILL.md')
MAX_LINHAS_SKILL = 300
SECOES = [  # titulos (regex, case-insensitive) que o SKILL.md v2 precisa ter
    r'^## .*quatro l[aâ]minas',
    r'^## .*juiz (por|sobre o) diff',
    r'^## .*hooks',
    r'^## .*paralelismo',
    r'^## .*plano.*fonte',
    r'^## .*(gasto|custo) .*rodada',
    r'^## .*ferramentas da esteira',
    r'^## .*ferramentas de teste',
    r'^## .*r[eé]gua de escalada',
    r'^## .*armadilhas',
    r'^## .*fechos',
]
ARQUIVOS = [
    'scripts/juiz.py', 'scripts/test_juiz.py',
    'scripts/triagem.py', 'scripts/rubrica.py', 'scripts/dupla.py', 'scripts/custo_historico.py',
    'scripts/decisoes.py', 'scripts/iniciar.py', 'scripts/prova_hook_vivo.py', 'scripts/loop_init.py',
    'scripts/test_v3.py', 'scripts/test_hook.py',
    'scripts/qualidade.py', 'scripts/smoke_web.py', 'scripts/test_qualidade.py',
    'assets/eslint.config.base.mjs', 'assets/playwright/smoke.spec.js', 'assets/playwright/playwright.config.js',
    'references/pesquisa-2026-09-06-v4.md', 'references/armadilhas.md',
    'scripts/ledger.py', 'scripts/test_ledger.py', 'references/sommelier.md', 'references/paralelismo.md',
    'assets/hooks.exemplo.json', 'assets/solucao.modelo.txt', 'assets/portao-hook.py',
    'assets/rubricas/bot.txt', 'assets/rubricas/site.txt', 'assets/rubricas/script-agendado.txt',
    'assets/rubricas/receita-maquina.txt', 'assets/rubricas/skill.txt',
    'references/pesquisa-2026-09-05.md', 'references/pesquisa-2026-09-05-v3.md', 'references/scripts.md',
    'references/pesquisa-2026-09-06-v6.md',
]
SEGREDO = re.compile(r'(sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|'
                     r'senha\s*[:=]\s*\S{6,}|password\s*[:=]\s*\S{6,})', re.I)

falhas = []


def ok(cond, msg):
    print(('  ok  ' if cond else '  FAIL') + ' ' + msg)
    if not cond:
        falhas.append(msg)


def ler(caminho):
    with open(caminho, 'rb') as f:
        return f.read()


def main():
    print('[prova ocombo]')
    ok(os.path.exists(SKILL), 'SKILL.md existe')
    if not os.path.exists(SKILL):
        return 1
    bruto = ler(SKILL)
    ok(b'\r\n' not in bruto, 'SKILL.md em LF (sem CRLF)')
    texto = bruto.decode('utf-8')
    linhas = texto.split('\n')
    ok(linhas[0] == '---' and re.search(r'^name: ocombo$', texto, re.M) is not None,
       'frontmatter name: ocombo')
    ok(len(linhas) <= MAX_LINHAS_SKILL,
       'SKILL.md <= %d linhas (tem %d)' % (MAX_LINHAS_SKILL, len(linhas)))
    ok(re.search(r'(?<!\\)\$(\{?\d|ARGUMENTS)', texto) is None,
       'SKILL.md sem `$<digito>`/`${N}`/`$ARGUMENTS` cru (substituicao de argumentos; use \\$)')
    for sec in SECOES:
        ok(re.search(sec, texto, re.I | re.M) is not None, 'secao presente: ' + sec)
    smd = os.path.join(AQUI, 'references', 'scripts.md')
    stexto = ler(smd).decode('utf-8') if os.path.exists(smd) else ''
    for rel in ARQUIVOS:
        cam = os.path.join(AQUI, rel)
        ok(os.path.exists(cam), 'arquivo referenciado existe: ' + rel)
        if os.path.exists(cam):
            ok(b'\r\n' not in ler(cam), 'LF: ' + rel)
            nome = rel.rsplit('/', 1)[-1]
            ok(rel in texto or nome in stexto or rel in stexto,
               'SKILL.md ou references/scripts.md cita ' + rel)
    # fontes: toda URL citada no SKILL.md tem que estar na pesquisa auditada
    pesqs = [os.path.join(AQUI, 'references', n) for n in ('pesquisa-2026-09-05.md', 'pesquisa-2026-09-05-v3.md', 'pesquisa-2026-09-06-v4.md', 'pesquisa-2026-09-06-v6.md')]
    if all(os.path.exists(p) for p in pesqs):
        ptexto = ''.join(ler(p).decode('utf-8') for p in pesqs)
        urls = set(u.rstrip('.,;:') for u in re.findall(r'https?://[^\s)>\]]+', texto))
        ok(len(urls) >= 5, 'SKILL.md cita >= 5 URLs (tem %d)' % len(urls))
        for u in sorted(urls):
            ok(u in ptexto, 'URL do SKILL.md consta na pesquisa: ' + u)
        ok(ptexto.count('"') >= 20, 'pesquisa traz trechos literais (>= 10 citacoes)')
    rdir = os.path.join(AQUI, 'assets', 'rubricas')
    for a in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        t = ler(os.path.join(rdir, a)).decode('utf-8')
        ok(len(re.findall(r'^C\d+\.', t, re.M)) >= 3 and 'REGRESS' in t,
           'rubrica %s: >= 3 criterios numerados e REGRESSAO' % a)
    # segredo em tudo que viaja pelo canal
    for raiz, _, arqs in os.walk(AQUI):
        if '__pycache__' in raiz:
            continue
        for a in arqs:
            if a.endswith(('.md', '.py', '.json', '.txt', '.bat', '.js', '.mjs')):
                cam = os.path.join(raiz, a)
                t = ler(cam).decode('utf-8', 'replace')
                ok(SEGREDO.search(t) is None, 'sem segredo: ' + os.path.relpath(cam, AQUI))
    # decisoes herdadas que NAO podem sumir
    for frase in ['grupo de relatórios do WhatsApp', 'cross-model', 'exit code', 'ssh', 'SHA-256', 'dinheiro', 'terceiro',
                  'aprovado.sha256', 'CONFORMIDADE', '--balanco']:  # v6
        ok(frase in texto, 'SKILL.md preserva: ' + frase)
    # testes unitarios do juiz (sem chamar claude)
    tj = os.path.join(AQUI, 'scripts', 'test_juiz.py')
    if os.path.exists(tj):
        r = subprocess.run([sys.executable, '-m', 'unittest', '-q', 'test_juiz', 'test_v3', 'test_hook', 'test_qualidade', 'test_ledger'],
                           cwd=os.path.join(AQUI, 'scripts'), capture_output=True, text=True)
        print(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '')
        ok(r.returncode == 0, 'unittest test_juiz + test_v3 + test_hook + test_qualidade verdes (exit %d)' % r.returncode)
    # v4: o linter da propria skill (ruff F/E9 + eslint) tem de estar verde
    rq = subprocess.run([sys.executable, os.path.join(AQUI, 'scripts', 'qualidade.py'), AQUI, '--so', 'py'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace')
    ok(rq.returncode == 0, 'qualidade.py (ruff F/E9) verde na propria skill (exit %d)' % rq.returncode)
    print('\n%d falha(s)' % len(falhas))
    return 1 if falhas else 0


if __name__ == '__main__':
    sys.exit(main())
