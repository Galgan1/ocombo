# -*- coding: utf-8 -*-
"""Portao do repositorio publico da skill ocombo (verde = exit 0). Roda na CI e antes de cada push.

Checa:
  1. a prova da propria skill (prova.py na raiz) esta verde — forma, testes puros, ruff;
  2. as pecas do repo existem (README, LICENSE, .gitattributes, .gitignore, workflow) e o README cita
     a instalacao e os scripts principais;
  3. nada da maquina do autor: caminho absoluto de usuario, unidade de rede, link de artefato/sessao privada;
  4. nada pessoal: telefone, e-mail, CPF/CNPJ, token/chave (padroes) em qualquer arquivo de texto;
  5. se existir o mapa local (~/.claude/ocombo-publicar.json), nenhum termo 'proibido' dele sobrou
     em NENHUM arquivo (README e LICENSE inclusive: privacidade total desde 08/09/2026);
  6. todo texto em LF e UTF-8; nenhum cache (__pycache__, .ruff_cache) versionado;
  7. metadados do git: autor e committer de TODOS os commits com e-mail noreply do GitHub, mensagem sem
     link de sessao/artefato privado e sem e-mail que nao seja o noreply (os testes puros em
     tools/test_prova_repo.py cobrem a regra; a CI faz checkout com fetch-depth 0 para ver a historia);
  8. os testes puros das ferramentas (tools/test_*.py) verdes.
Uso: python tools/prova_repo.py [--sem-skill]   (--sem-skill pula o item 1, para rodar rapido)
"""
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
MAPA = os.path.join(os.path.expanduser('~'), '.claude', 'ocombo-publicar.json')
TEXTO = ('.md', '.py', '.txt', '.json', '.js', '.mjs', '.bat', '.sh', '.yml', '.yaml', '.cfg', '.toml')
IGNORAR = ('.git', 'node_modules', '__pycache__', '.ruff_cache')
FORA_DA_LISTA_PRIVADA = ()  # desde 08/09/2026 nenhum arquivo escapa da lista privada

GENERICOS = [  # (nome, regex) — valem para qualquer repo publico
    ('caminho de usuario Windows', r'[A-Za-z]:\\+Users\\+[A-Za-z]'),
    ('caminho de usuario POSIX', r'(/c|/mnt/c)/Users/[A-Za-z]|/home/[a-z]+/'),
    ('unidade de rede / Drive', r'Meu[ ]Drive|One[D]rive'),
    ('artefato ou sessao privada', r'claude\.ai/code/(artifact|session)'),
    ('telefone', r'(?<![\w/.-])(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}(?![\w/.-])'),
    ('e-mail', r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}'),
    ('CPF', r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'),
    ('CNPJ', r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b'),
    ('token/chave', r'sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{10,}'),
    ('senha literal', r'(senha|password)\s*[:=]\s*[\'"]?[A-Za-z0-9@#$%!*]{6,}'),
]
RX_NOREPLY = re.compile(r'^\d+\+[A-Za-z0-9-]+@users\.noreply\.github\.com$')
RX_EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}')
EMAILS_OK_NA_MENSAGEM = ('@anthropic.com', '@users.noreply.github.com')
EXCECOES = {  # trechos legitimos que casam com um padrao acima (a URL de fonte nao e telefone)
    'telefone': [r'arxiv\.org/abs/\d{4}\.\d{5}', r'\b20\d{2}-\d{2}-\d{2}\b', r'\d{4}-\d{4}\s*\)?\s*(Wiley|IEEE)', r'\(?\d{10} = 0x[0-9A-Fa-f]{8}'],
}

falhas = []


def ok(cond, msg):
    print(('  ok  ' if cond else '  FAIL') + ' ' + msg)
    if not cond:
        falhas.append(msg)


def arquivos_texto(repo):
    for raiz, pastas, arqs in os.walk(repo):
        pastas[:] = [p for p in pastas if p not in IGNORAR]
        for a in arqs:
            if a.endswith(TEXTO) or a in ('LICENSE',):
                yield os.path.relpath(os.path.join(raiz, a), repo).replace('\\', '/')


def _sem_excecoes(nome, texto):
    for e in EXCECOES.get(nome, []):
        texto = re.sub(e, ' ', texto)
    return texto


def varrer(repo, proibidos=()):
    """Devolve a lista de problemas (vazia = limpo). Usada tambem por publicar.py."""
    problemas = []
    for rel in arquivos_texto(repo):
        cam = os.path.join(repo, rel)
        with open(cam, 'rb') as f:
            bruto = f.read()
        if b'\r\n' in bruto:
            problemas.append('CRLF em ' + rel)
        try:
            texto = bruto.decode('utf-8')
        except UnicodeDecodeError:
            problemas.append('nao e UTF-8: ' + rel)
            continue
        for nome, rx in GENERICOS:
            m = re.search(rx, _sem_excecoes(nome, texto), re.I)
            if m:
                problemas.append('%s em %s: %r' % (nome, rel, m.group(0)[:40]))
        if rel in FORA_DA_LISTA_PRIVADA:
            continue
        for rx in proibidos:
            m = re.search(rx, texto, re.I)
            if m:
                problemas.append('termo privado em %s: %r (regex %s)' % (rel, m.group(0)[:40], rx))
    # cache VERSIONADO e problema; cache solto no disco nao (o proprio prova.py cria __pycache__ ao testar)
    try:
        r = subprocess.run(['git', 'ls-files', '--cached'], cwd=repo, capture_output=True, text=True)
        rastreados = r.stdout.splitlines() if r.returncode == 0 else []
    except OSError:
        rastreados = []
    for rel in rastreados:
        if '__pycache__' in rel or '.ruff_cache' in rel or rel.endswith('.pyc'):
            problemas.append('cache versionado no git: ' + rel)
    return problemas


def parse_log(bruto):
    """Texto de `git log --format=%H%x1f%ae%x1f%ce%x1f%B%x1e` -> [(sha, email_autor, email_committer, msg)]."""
    regs = []
    for bloco in bruto.split('\x1e'):
        bloco = bloco.strip('\n')
        if not bloco.strip():
            continue
        partes = bloco.split('\x1f', 3)
        if len(partes) == 4:
            regs.append((partes[0].strip(), partes[1].strip(), partes[2].strip(), partes[3].strip('\n')))
    return regs


def problemas_git(registros):
    """Privacidade nos metadados: e-mail noreply em autor/committer; mensagem sem link privado nem e-mail."""
    problemas = []
    for sha, ea, ec, msg in registros:
        for papel, e in (('autor', ea), ('committer', ec)):
            if not RX_NOREPLY.match(e):
                problemas.append('%s: e-mail de %s nao e o noreply do GitHub: %s' % (sha[:8], papel, e))
        if re.search(r'claude\.ai/code/', msg):
            problemas.append('%s: link de sessao/artefato privado na mensagem' % sha[:8])
        for e in RX_EMAIL.findall(msg):
            if not e.endswith(EMAILS_OK_NA_MENSAGEM):
                problemas.append('%s: e-mail na mensagem: %s' % (sha[:8], e))
    return problemas


def registros_git(repo):
    # --branches (ramos locais), nao --all: o origin/main so muda no push, e o portao roda ANTES dele
    r = subprocess.run(['git', 'log', '--branches', '--format=%H%x1f%ae%x1f%ce%x1f%B%x1e'], cwd=repo,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None
    return parse_log(r.stdout)


def main(argv):
    print('[prova repo ocombo] ' + REPO)
    sem_skill = '--sem-skill' in argv
    for peca in ('README.md', 'LICENSE', '.gitattributes', '.gitignore', '.github/workflows/prova.yml',
                 'SKILL.md', 'prova.py', 'tools/publicar.py'):
        ok(os.path.exists(os.path.join(REPO, peca)), 'peca do repo existe: ' + peca)
    readme = open(os.path.join(REPO, 'README.md'), encoding='utf-8').read() if os.path.exists(os.path.join(REPO, 'README.md')) else ''
    for trecho in ('git clone', 'scripts/juiz.py', 'scripts/iniciar.py', 'prova.py', 'LICENSE', 'Claude Code'):
        ok(trecho in readme, 'README cita: ' + trecho)
    lic = open(os.path.join(REPO, 'LICENSE'), encoding='utf-8').read() if os.path.exists(os.path.join(REPO, 'LICENSE')) else ''
    ok(lic.startswith('MIT License'), 'LICENSE e MIT')
    proibidos = []
    if os.path.exists(MAPA):
        with open(MAPA, encoding='utf-8') as f:
            proibidos = json.load(f).get('proibidos', [])
        print('  (mapa local: %d termos privados vigiados)' % len(proibidos))
    else:
        print('  (sem mapa local: so as checagens genericas)')
    problemas = varrer(REPO, proibidos)
    ok(not problemas, 'varredura de dados da maquina/pessoais limpa (%d achado(s))' % len(problemas))
    for p in problemas:
        print('        - ' + p)
    regs = registros_git(REPO)
    ok(regs is not None and len(regs) > 0, 'historia do git legivel (%s commit(s))' % (len(regs) if regs else 0))
    pg = problemas_git(regs or [])
    ok(not pg, 'metadados do git sem e-mail pessoal nem link privado (%d achado(s))' % len(pg))
    for p in pg:
        print('        - ' + p)
    t = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', AQUI, '-p', 'test_*.py'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    cauda = [ln for ln in (t.stderr or '').splitlines() if ln.strip()][-1:] or ['']
    ok(t.returncode == 0, 'testes puros das ferramentas verdes (exit %d: %s)' % (t.returncode, cauda[0].strip()))
    if not sem_skill:
        r = subprocess.run([sys.executable, os.path.join(REPO, 'prova.py')], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        cauda = [ln for ln in (r.stdout or '').splitlines() if ln.strip()][-1:] or ['']
        ok(r.returncode == 0, 'prova.py da skill verde (exit %d: %s)' % (r.returncode, cauda[0].strip()))
        if r.returncode != 0:
            print('\n'.join(ln for ln in (r.stdout or '').splitlines() if 'FAIL' in ln))
    print('\n%d falha(s)' % len(falhas))
    return 1 if falhas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
