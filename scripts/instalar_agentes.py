# -*- coding: utf-8 -*-
"""Instala os PAPEIS do combo como subagentes (v10, 10/09/2026).

Os tres papeis viajam pelo canal dentro da skill (`assets/agentes/*.md`) e sao instalados como
subagentes do usuario em `~/.claude/agents/`. Assim a receita e versionada (Akita) e a mesma em casa,
na outra máquina e onde mais a skill chegar. Idempotente: reescreve so o que divergiu.

Uso:
  python instalar_agentes.py             instala/atualiza em ~/.claude/agents
  python instalar_agentes.py --verificar exit 1 se faltar arquivo ou o conteudo divergir (portao)
  python instalar_agentes.py --destino <pasta>
"""
import argparse
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGEM = os.path.join(os.path.dirname(AQUI), 'assets', 'agentes')
DESTINO_PADRAO = os.path.join(os.path.expanduser('~'), '.claude', 'agents')
PAPEIS = ('ocombo-grelha', 'ocombo-executor', 'ocombo-juiz')
# Ferramenta de escrita que o papel JUIZ nao pode ter: quem julga nao conserta.
ESCRITA = ('Edit', 'Write', 'NotebookEdit')


def frontmatter(texto):
    """Devolve o dict cru do frontmatter (valor como string, sem YAML de verdade: campos simples)."""
    if not texto.startswith('---\n'):
        return {}
    fim = texto.find('\n---\n', 4)
    if fim < 0:
        return {}
    campos, chave = {}, None
    for linha in texto[4:fim].split('\n'):
        m = re.match(r'^([a-zA-Z]+):\s*(.*)$', linha)
        if m:
            chave = m.group(1)
            campos[chave] = m.group(2).strip()
        elif chave and linha.strip():
            campos[chave] = (campos[chave] + ' ' + linha.strip()).strip()
    return campos


def validar(texto, nome):
    """Problemas do arquivo de papel (lista vazia = valido). Puro: os testes chamam sem tocar disco."""
    fm = frontmatter(texto)
    probs = []
    if not fm:
        return ['%s: sem frontmatter YAML' % nome]
    if fm.get('name') != nome:
        probs.append('%s: name do frontmatter ("%s") != nome do arquivo' % (nome, fm.get('name')))
    desc = fm.get('description', '')
    if len(desc) < 80 or 'Use ' not in desc:
        probs.append('%s: description precisa dizer QUANDO delegar (>= 80 chars com "Use ...")' % nome)
    if not fm.get('model'):
        probs.append('%s: sem model (use inherit ou um tier explicito)' % nome)
    ferramentas = [t.strip() for t in fm.get('tools', '').split(',') if t.strip()]
    negadas = [t.strip() for t in fm.get('disallowedTools', '').split(',') if t.strip()]
    if nome == 'ocombo-juiz':
        if fm.get('model') in ('inherit', '', None):
            probs.append('ocombo-juiz: cross-model e regra da casa — model nao pode ser inherit')
        tem = [t for t in ESCRITA if t in ferramentas]
        if tem:
            probs.append('ocombo-juiz: nao pode ter ferramenta de escrita (%s)' % ', '.join(tem))
        falta = [t for t in ESCRITA if t not in negadas]
        if falta:
            probs.append('ocombo-juiz: falta negar explicitamente %s' % ', '.join(falta))
    if nome == 'ocombo-grelha' and 'Edit' in ferramentas:
        probs.append('ocombo-grelha: quem pergunta nao edita codigo (Edit na lista de tools)')
    if ferramentas and 'Agent' in ferramentas:
        probs.append('%s: papel nao abre subagente (Agent na lista de tools)' % nome)
    return probs


def _ler(cam):
    with open(cam, 'rb') as f:
        return f.read().replace(b'\r\n', b'\n')


def estado(destino=DESTINO_PADRAO):
    """(problemas, divergentes): o que esta invalido na origem e o que falta/difere no destino."""
    probs, divergentes = [], []
    for nome in PAPEIS:
        org = os.path.join(ORIGEM, nome + '.md')
        if not os.path.exists(org):
            probs.append('%s: arquivo do papel nao existe em assets/agentes' % nome)
            continue
        bruto = _ler(org)
        probs += validar(bruto.decode('utf-8'), nome)
        dst = os.path.join(destino, nome + '.md')
        if not os.path.exists(dst) or _ler(dst) != bruto:
            divergentes.append(nome)
    return probs, divergentes


def instalar(destino=DESTINO_PADRAO):
    probs, divergentes = estado(destino)
    if probs:
        return probs, []
    os.makedirs(destino, exist_ok=True)
    for nome in divergentes:
        with open(os.path.join(destino, nome + '.md'), 'wb') as f:
            f.write(_ler(os.path.join(ORIGEM, nome + '.md')))
    return [], divergentes


def main(argv=None):
    ap = argparse.ArgumentParser(description='Instala os papeis do combo como subagentes.')
    ap.add_argument('--destino', default=DESTINO_PADRAO)
    ap.add_argument('--verificar', action='store_true')
    a = ap.parse_args(argv)
    if a.verificar:
        probs, divergentes = estado(a.destino)
        for p in probs:
            print('FAIL ' + p)
        for d in divergentes:
            print('FAIL %s: ausente ou diferente em %s' % (d, a.destino))
        print('%d problema(s)' % (len(probs) + len(divergentes)))
        return 1 if (probs or divergentes) else 0
    probs, escritos = instalar(a.destino)
    for p in probs:
        print('FAIL ' + p)
    if probs:
        return 1
    print('ok  %d papel(is) atualizado(s) em %s%s'
          % (len(escritos), a.destino, (': ' + ', '.join(escritos)) if escritos else ' (ja iguais)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
