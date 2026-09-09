# -*- coding: utf-8 -*-
"""Historico de gasto que atravessa projetos.

juiz.py anexa cada linha tambem em %USERPROFILE%/.claude/ocombo-custo.log (LOCAL, fora do canal), com o
nome da instancia. Este script le esse arquivo (ou o que for passado) e imprime a tabela por instancia:
rodadas, USD total, USD por rodada, segundos, e o TOTAL geral.
Uso: python custo_historico.py [arquivo.log]
"""
import os
import re
import sys

PADRAO = os.path.join(os.path.expanduser('~'), '.claude', 'ocombo-custo.log')
RE = re.compile(r'^(?P<ts>\S+)\s+(?P<inst>\S+)\s+(?P<rod>r\d+|rubrica|dupla)\s+(?P<modelo>\S+)\s+(?P<resto>.*)$')


def parse(linha):
    m = RE.match(linha.strip())
    if not m:
        return None
    d = m.groupdict()
    kv = dict(re.findall(r'(\w+)=([^\s]+)', d['resto']))
    d['usd'] = float(kv['usd']) if 'usd' in kv and kv['usd'] != 'None' else None
    d['s'] = float(kv['s']) if 's' in kv and kv['s'] != 'None' else None
    d['sem_usage'] = 'sem usage' in d['resto']
    return d


def tabela(linhas):
    por = {}
    for l in linhas:
        d = parse(l)
        if not d:
            continue
        e = por.setdefault(d['inst'], {'rodadas': 0, 'usd': 0.0, 's': 0.0, 'sem': 0})
        e['rodadas'] += 1
        if d['usd'] is None:
            e['sem'] += 1
        else:
            e['usd'] += d['usd']
        e['s'] += d['s'] or 0.0
    out = ['%-28s %7s %9s %9s %8s %s' % ('instancia', 'rodadas', 'USD', 'USD/rod', 'seg', 'sem-usage')]
    tu = ts = tr = 0.0
    for inst, e in sorted(por.items()):
        out.append('%-28s %7d %9.2f %9.2f %8.0f %s' % (inst, e['rodadas'], e['usd'],
                   e['usd'] / e['rodadas'] if e['rodadas'] else 0, e['s'], e['sem'] or ''))
        tu += e['usd']; ts += e['s']; tr += e['rodadas']
    out.append('%-28s %7d %9.2f %9.2f %8.0f' % ('TOTAL', tr, tu, tu / tr if tr else 0, ts))
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    arq = sys.argv[1] if len(sys.argv) > 1 else PADRAO
    if not os.path.exists(arq):
        print('sem historico em', arq)
        sys.exit(1)
    with open(arq, encoding='utf-8', errors='replace') as f:
        print(tabela(f.readlines()))
