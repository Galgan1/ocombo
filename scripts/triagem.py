# -*- coding: utf-8 -*-
"""Triagem DETERMINISTICA da instancia (0 tokens) + manifesto de arquivos (identificadores leves).

triagem(pasta) -> lista de problemas ([] = passou). Cobre o que um modelo nao precisa ler para achar:
  ESTADO presente · RUBRICA com criterios numerados (C1., C2., ...) e um criterio de REGRESSAO ·
  SOLUCAO presente · todo caminho relativo citado (evidencias/..., corpus/..., historico/...) existe.
manifesto(pasta) -> texto "caminho  bytes  sha256[:12]" de tudo que o juiz pode abrir (sem historico/,
  __pycache__, veredicto.md, delta.patch, manifesto.txt); tambem grava manifesto.txt.
Uso: python triagem.py <pasta>   (exit 0 = passou; 1 = problemas listados)
"""
import hashlib
import os
import re
import sys

IGNORAR_DIRS = {'historico', '__pycache__', '.git'}
IGNORAR_ARQS = {'veredicto.md', 'delta.patch', 'manifesto.txt'}
RE_CAMINHO = re.compile(r'\b((?:evidencias|corpus|historico|assets|scripts|references)/[A-Za-z0-9_./\-]+)')


def _ler(cam):
    with open(cam, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _secao(texto, nome):
    m = re.search(r'^=== ' + nome + r'\b[^\n]*\n(.*?)(?=^=== |\Z)', texto, re.M | re.S)
    return m.group(1) if m else None


def triagem(pasta):
    probs = []
    sol = os.path.join(pasta, 'solucao.txt')
    if not os.path.exists(sol):
        return ['solucao.txt nao existe']
    t = _ler(sol)
    if _secao(t, 'ESTADO') is None:
        probs.append('sem secao ESTADO no topo (fonte unica)')
    rub = _secao(t, 'RUBRICA')
    if rub is None:
        probs.append('sem secao RUBRICA')
    else:
        if not re.search(r'^\s*C\d+\.', rub, re.M):
            probs.append('RUBRICA sem criterio numerado (C1., C2., ...)')
        if not re.search(r'REGRESS', rub, re.I):
            probs.append('RUBRICA sem criterio de REGRESSAO (o que passava continua passando)')
    sol_txt = _secao(t, 'SOLUCAO')
    if sol_txt is None:
        probs.append('sem secao SOLUCAO')
    # so o que a SOLUCAO/ENTREGA AFIRMA existir e checado; a RUBRICA descreve expectativa (pode citar
    # arquivo que so nasce na ENTREGA) — regra fixada em 05/09/2026 apos a triagem reprovar a propria rubrica
    alvo = (sol_txt or '') + (_secao(t, 'ENTREGA') or '')
    for cam in sorted(set(RE_CAMINHO.findall(alvo))):
        cam_limpo = cam.rstrip('.,;:)')
        if not os.path.exists(os.path.join(pasta, cam_limpo)):
            probs.append('caminho citado nao existe na instancia: ' + cam_limpo)
    return probs


def manifesto(pasta):
    linhas = []
    for raiz, dirs, arqs in os.walk(pasta):
        dirs[:] = sorted(d for d in dirs if d not in IGNORAR_DIRS)
        for a in sorted(arqs):
            if a in IGNORAR_ARQS:
                continue
            cam = os.path.join(raiz, a)
            rel = os.path.relpath(cam, pasta).replace('\\', '/')
            with open(cam, 'rb') as f:
                b = f.read()
            linhas.append('%s  %d  %s' % (rel, len(b), hashlib.sha256(b).hexdigest()[:12]))
    texto = '# manifesto da instancia (caminho  bytes  sha256[:12]) - abra so o que a SOLUCAO cita\n' + '\n'.join(linhas) + '\n'
    with open(os.path.join(pasta, 'manifesto.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)
    return texto


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    p = triagem(sys.argv[1])
    print('\n'.join(p) if p else '[triagem] ok')
    sys.exit(1 if p else 0)
