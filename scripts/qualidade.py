# -*- coding: utf-8 -*-
"""Portao de qualidade estatica do ocombo (0 tokens): linter em Python e JavaScript, exit code honesto.

Uso:  python qualidade.py <repo> [--saida arquivo.txt] [--so py|js] [--max-erros N]
  exit 0 = nenhum erro; 1 = erro de lint; 2 = ferramenta ausente ou uso errado.

Roda `python -m ruff check --select F,E9` (nome indefinido, import/variavel sem uso, sintaxe; NADA de
estilo) nos .py e `eslint` (config fixa em assets/eslint.config.base.mjs: no-undef, no-unused-vars e as regras
de correcao do recommended) nos .js/.mjs/.cjs. Ignora node_modules, .git, dist, build, __pycache__, venv,
historico, corpus, dist-*/build-*, *.min.js, bundle minificado (alguma linha > 3000 chars) e arquivo que o
git do repo ignora (`git check-ignore`). O sourceType de cada .js vem do package.json mais proximo que
declara "type" (subindo ate a raiz passada; v 16/10/2026): os arquivos vao ao eslint em dois grupos,
OCOMBO_ESLINT_MODULE=1 (module) e =0 (commonjs); a linha do relatorio mostra esm=1, esm=0 ou esm=1:N/0:M.
Pega exatamente o que a suite nao pega: simbolo orfao apos extracao de modulo (bot caiu 2 min em
29/08/2026), variavel de outro arquivo, import quebrado.

Onde o eslint vem: node_modules/.bin do proprio repo -> $OCOMBO_NODE_TOOLS/node_modules/.bin -> `npx -y`.
Relatorio: uma linha por achado (arquivo:linha regra mensagem) + totais + EXIT= no fim; --saida grava o mesmo texto.
"""
import json
import os
import shutil
import subprocess
import sys

IGNORAR = {'node_modules', '.git', '.claude', 'dist', 'build', '__pycache__', 'venv', '.venv', 'historico', 'corpus'}  # .claude = worktrees de sessoes
# Pastas de build com sufixo (dist-prod, dist-sandbox do Vite; build-*): tambem sao saida gerada.
PREFIXOS_IGNORADOS = ('dist-', 'build-')
EXT_JS = ('.js', '.mjs', '.cjs')
LINHA_MINIFICADA = 3000
NL = chr(10)
BS1 = chr(92)
BS2 = chr(92) * 2
AQUI = os.path.dirname(os.path.abspath(__file__))
CONFIG_ESLINT = os.path.join(AQUI, '..', 'assets', 'eslint.config.base.mjs')


def listar(repo, exts):
    """Arquivos com as extensoes dadas, pulando pastas ignoradas (logica pura, testavel)."""
    achados = []
    for raiz, pastas, arqs in os.walk(repo):
        pastas[:] = [p for p in pastas if p not in IGNORAR and not p.startswith(PREFIXOS_IGNORADOS)]
        for a in arqs:
            if a.endswith(exts) and not a.endswith('.min.js'):
                achados.append(os.path.join(raiz, a))
    return sorted(achados)


def minificado(caminho, limite=LINHA_MINIFICADA):
    """True se ALGUMA linha passa do limite (bundle gerado: nao se linta).

    Ate 06/09/2026 so as 5 primeiras linhas eram olhadas; o bundle do Vite abre com cabecalho de licenca em
    linhas curtas e a linha longa vem depois (linha 17+ em public/assets/index-*.js) — 89 dos 122 achados da
    api-do-projeto e 44 dos 46 do client eram bundle (ciclo do painel interno, 06/09/2026).
    """
    try:
        with open(caminho, 'r', encoding='utf-8', errors='replace') as f:
            for linha in f:
                if len(linha) > limite:
                    return True
    except OSError:
        return False
    return False


def sem_ignorados(arquivos, ignorados):
    """Remove da lista os caminhos que o git ignora (logica pura). Comparacao por caminho normalizado."""
    norm = lambda c: os.path.normcase(os.path.abspath(c))
    fora = {norm(i) for i in ignorados}
    return [a for a in arquivos if norm(a) not in fora]


def ignorados_pelo_git(repo, arquivos):
    """Caminhos (absolutos) que `git check-ignore` reconhece como ignorados; [] fora de um repo git ou sem git.

    POR QUE (06/09/2026): db/modulo*.js e routes/modulo.js estao gitignorados no tronco do projeto (sao de outra
    receita de deploy) — nao sao codigo do repo e nao devem contar no lint do repo. O git recebe caminhos
    RELATIVOS com barra normal (absoluto Windows volta citado; /c/... do Git Bash e "Invalid path").
    """
    if not arquivos:
        return []
    rel = {os.path.relpath(a, repo).replace(os.sep, '/'): a for a in arquivos}
    try:
        # bytes, nao text=True: no Windows o modo texto troca o \n de entrada por \r\n e o git le "db/x.js\r"
        # (nenhum caminho bate; medido em 06/09/2026).
        proc = subprocess.run(['git', 'check-ignore', '--stdin'], cwd=repo, input=(NL.join(rel) + NL).encode('utf-8'),
                              capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode not in (0, 1):      # 128 = nao e repo git / caminho invalido
        return []
    achados = []
    for linha in proc.stdout.decode('utf-8', 'replace').splitlines():
        linha = linha.strip()
        if linha.startswith('"') and linha.endswith('"'):
            linha = linha[1:-1].replace(BS2, BS1)
        if linha in rel:
            achados.append(rel[linha])
    return achados


def lotes(itens, tamanho=40):
    """Divide a lista em lotes: o Windows limita a linha de comando (WinError 206 com ~300 arquivos e o cmd.exe do shim do eslint estoura em 8 kB, 06/09/2026)."""
    return [itens[i:i + tamanho] for i in range(0, len(itens), tamanho)]


def repo_esm(repo):
    """True se package.json do repo declara "type": "module"."""
    pj = os.path.join(repo, 'package.json')
    try:
        with open(pj, encoding='utf-8') as f:
            return json.load(f).get('type') == 'module'
    except (OSError, ValueError):
        return False


def _type_declarado(pasta, cache):
    """'module'/'commonjs'/... se o package.json da pasta declara "type"; None se nao ha arquivo ou campo."""
    if pasta not in cache:
        try:
            with open(os.path.join(pasta, 'package.json'), encoding='utf-8') as f:
                tipo = json.load(f).get('type')
        except (OSError, ValueError, AttributeError):
            tipo = None
        cache[pasta] = tipo if isinstance(tipo, str) else None
    return cache[pasta]


def esm_por_arquivo(arquivo, repo, cache=None):
    """True se o package.json mais proximo QUE DECLARA "type" (subindo ate a raiz passada) diz "module".

    POR QUE (16/10/2026, ciclo de revisão de um site): so a raiz era lida; o site tem a raiz sem "type" e
    app/client/package.json com "type": "module" — 85 Parsing error falsos. Regra do Node: vale o package.json
    mais proximo. package.json SEM "type" no meio do caminho nao corta a subida (o Node o leria como commonjs,
    mas subprojeto de bundler sem "type" sob raiz ESM passava hoje e nao pode passar a falhar). Nenhum
    package.json com "type" ate a raiz = como antes (commonjs).
    """
    cache = {} if cache is None else cache
    raiz = os.path.normcase(os.path.abspath(repo))
    pasta = os.path.dirname(os.path.abspath(arquivo))
    while True:
        tipo = _type_declarado(pasta, cache)
        if tipo is not None:
            return tipo == 'module'
        if os.path.normcase(pasta) == raiz or os.path.dirname(pasta) == pasta:
            return False
        pasta = os.path.dirname(pasta)


def agrupar_por_esm(arquivos, repo):
    """{'1': [...module], '0': [...commonjs]} na ordem de entrada; grupo vazio nao aparece (logica pura)."""
    cache, grupos = {}, {}
    for a in arquivos:
        grupos.setdefault('1' if esm_por_arquivo(a, repo, cache) else '0', []).append(a)
    return grupos


def rotulo_esm(grupos):
    """Texto do esm= no relatorio: '1' ou '0' quando homogeneo (igual a antes); '1:N/0:M' quando misto."""
    if len(grupos) == 1:
        return next(iter(grupos))
    return '/'.join('%s:%d' % (k, len(grupos[k])) for k in ('1', '0') if k in grupos)


def resumir_ruff(saida_json):
    """JSON do ruff -> lista de (arquivo, linha, regra, mensagem)."""
    try:
        itens = json.loads(saida_json or '[]')
    except ValueError:
        return [('?', 0, 'RUFF-JSON', 'saida ilegivel: ' + (saida_json or '')[:120])]
    return [(i.get('filename', '?'), (i.get('location') or {}).get('row', 0), i.get('code') or '?',
             i.get('message', '')) for i in itens]


def resumir_eslint(saida_json):
    """JSON do eslint -> lista de (arquivo, linha, regra, mensagem); so severity 2 (erro)."""
    try:
        arquivos = json.loads(saida_json or '[]')
    except ValueError:
        return [('?', 0, 'ESLINT-JSON', 'saida ilegivel: ' + (saida_json or '')[:120])]
    out = []
    for f in arquivos:
        for m in f.get('messages', []):
            if m.get('severity') == 2:
                out.append((f.get('filePath', '?'), m.get('line', 0), m.get('ruleId') or 'fatal', m.get('message', '')))
    return out


def _eslint_cmd(repo):
    nome = 'eslint.cmd' if os.name == 'nt' else 'eslint'
    cand = [os.path.join(repo, 'node_modules', '.bin', nome)]
    tools = os.environ.get('OCOMBO_NODE_TOOLS')
    if tools:
        cand.append(os.path.join(tools, 'node_modules', '.bin', nome))
    for c in cand:
        if os.path.exists(c):
            return [c]
    return ['npx', '-y', '-p', 'eslint@10', 'eslint']


def rodar(cmd, cwd, env=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       shell=(os.name == 'nt'), env=env)
    return r.returncode, r.stdout, r.stderr


def por_regra(achados):
    """Contagem por regra, da mais frequente para a menos (logica pura)."""
    cont = {}
    for _, _, regra, _ in achados:
        cont[regra] = cont.get(regra, 0) + 1
    return sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))


def _fmt(achados, repo, max_erros):
    linhas = []
    if achados:
        linhas.append('  por regra: ' + ', '.join('%s %d' % kv for kv in por_regra(achados)))
    linhas += ['  %s:%s %s %s' % (os.path.relpath(a, repo) if os.path.isabs(a) else a, l, r, m)
               for a, l, r, m in achados[:max_erros]]
    return linhas


def main(argv):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if not argv or not os.path.isdir(argv[0]):
        print(__doc__)
        return 2
    repo = os.path.abspath(argv[0])
    saida, so, max_erros = None, None, 200
    i = 1
    while i < len(argv):
        if argv[i] == '--saida':
            saida = argv[i + 1]
            i += 2
        elif argv[i] == '--so':
            so = argv[i + 1]
            i += 2
        elif argv[i] == '--max-erros':
            max_erros = int(argv[i + 1])
            i += 2
        else:
            i += 1
    linhas = ['[qualidade] repo=' + repo]
    total = 0
    faltou = False

    pys = listar(repo, ('.py',)) if so in (None, 'py') else []
    pys = sem_ignorados(pys, ignorados_pelo_git(repo, pys))
    if pys:
        args_ruff = ['check', '--select', 'F,E9', '--output-format', 'json',
                     '--no-cache', '--exclude', ','.join(sorted(IGNORAR)), '.']
        code, out, err = rodar([sys.executable, '-m', 'ruff'] + args_ruff, repo)
        if 'No module named ruff' in err and shutil.which('ruff'):
            # v7 (07/09/2026): ruff instalado como binario (standalone, uv tool, brew), nao como modulo
            code, out, err = rodar([shutil.which('ruff')] + args_ruff, repo)
        if 'No module named ruff' in err:
            linhas.append('ruff: AUSENTE (pip install ruff, ou o binario ruff no PATH)')
            faltou = True
        else:
            achados = resumir_ruff(out)
            total += len(achados)
            linhas.append('ruff: %d arquivo(s) .py, %d erro(s)' % (len(pys), len(achados)))
            linhas += _fmt(achados, repo, max_erros)

    jss = [j for j in (listar(repo, EXT_JS) if so in (None, 'js') else []) if not minificado(j)]
    jss = sem_ignorados(jss, ignorados_pelo_git(repo, jss))
    if jss:
        grupos = agrupar_por_esm(jss, repo)   # sourceType por arquivo: package.json mais proximo (16/10/2026)
        achados, code, out, err, quebrou = [], 0, '[]', '', False
        for esm in ('1', '0'):
            env = dict(os.environ)
            env['OCOMBO_ESLINT_MODULE'] = esm
            for lote in lotes([os.path.relpath(j, repo) for j in grupos.get(esm, [])]):
                cmd = _eslint_cmd(repo) + ['--no-config-lookup', '--config', os.path.abspath(CONFIG_ESLINT),
                                           '--format', 'json', '--no-error-on-unmatched-pattern'] + lote
                code, out, err = rodar(cmd, repo, env)
                if not out.strip().startswith('['):
                    quebrou = True
                    break
                achados += resumir_eslint(out)
            if quebrou:
                break
        if quebrou:
            linhas.append('eslint: AUSENTE ou falhou (exit %d): %s' % (code, (err or out).strip()[:300]))
            faltou = True
        else:
            total += len(achados)
            linhas.append('eslint: %d arquivo(s) .js (esm=%s), %d erro(s)' % (len(jss), rotulo_esm(grupos), len(achados)))
            linhas += _fmt(achados, repo, max_erros)

    if not pys and not jss:
        linhas.append('nenhum .py ou .js encontrado')
    exit_code = 2 if faltou else (1 if total else 0)
    linhas.append('TOTAL erros=%d  EXIT=%d' % (total, exit_code))
    texto = '\n'.join(linhas)
    print(texto)
    if saida:
        with open(saida, 'w', encoding='utf-8') as f:
            f.write(texto + '\n')
    return exit_code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
