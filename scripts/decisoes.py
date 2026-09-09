# -*- coding: utf-8 -*-
"""Decisoes ja fechadas pelo dono, puxadas da memoria por grep (markdown + grep, sem RAG — Akita).

Uso: python decisoes.py <palavra> [palavra...] [--memoria <dir>]
Varre os .md da memoria (padrao: todas as pastas ~/.claude/projects/*/memory) e imprime as linhas que
tem MARCADOR de decisao + pelo menos uma palavra-chave (sem acento, sem caixa). Saida = rascunho do
"contexto herdado inviolavel" da grelha. Maximo 40 linhas.
"""
import glob
import os
import sys
import unicodedata

MARCADORES = ['decis', 'decidiu', 'ordem do dono', 'regra', 'nunca', 'sempre', 'padrao', 'proibid',
              'so com "sim"', 'fail-closed', 'exclusiv', 'correcao do dono']
LIMITE = 40


def _norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def buscar(textos, palavras):
    """textos: {nome: conteudo}. Devolve ['- [nome] linha', ...] ordenado por nome."""
    pal = [_norm(p) for p in palavras if p]
    marc = [_norm(m) for m in MARCADORES]
    saida = []
    for nome in sorted(textos):
        for linha in textos[nome].splitlines():
            n = _norm(linha)
            if not n.strip() or n.startswith(('---', 'name:', 'description:', 'metadata')):
                continue
            if any(m in n for m in marc) and (not pal or any(p in n for p in pal)):
                saida.append('- [%s] %s' % (nome, linha.strip()))
    return saida[:LIMITE]


def carregar(memoria_dir=None):
    if memoria_dir:
        arqs = glob.glob(os.path.join(memoria_dir, '*.md'))
    else:
        arqs = glob.glob(os.path.join(os.path.expanduser('~'), '.claude', 'projects', '*', 'memory', '*.md'))
    textos = {}
    for a in arqs:
        if os.path.basename(a) == 'MEMORY.md':
            continue
        with open(a, encoding='utf-8', errors='replace') as f:
            textos[os.path.basename(a)] = f.read()
    return textos


if __name__ == '__main__':
    try:  # console Windows em cp1252 quebra no primeiro acento (armadilha ja paga em 03/09/2026)
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    args = sys.argv[1:]
    mem = None
    if '--memoria' in args:
        i = args.index('--memoria')
        mem = args[i + 1]
        args = args[:i] + args[i + 2:]
    r = buscar(carregar(mem), args)
    print('\n'.join(r) if r else '(nenhuma decisao encontrada para: %s)' % ' '.join(args))
