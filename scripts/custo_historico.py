# -*- coding: utf-8 -*-
"""Historico de gasto que atravessa projetos.

juiz.py anexa cada linha tambem em %USERPROFILE%/.claude/ocombo-custo.log (LOCAL, fora do canal), com o
nome da instancia. Este script le esse arquivo (ou o que for passado) e imprime a tabela por instancia:
rodadas, USD total, USD por rodada, segundos, e o TOTAL geral.
Uso: python custo_historico.py [arquivo.log]            tabela por instancia
     python custo_historico.py --modelos [arquivo.log]  v13: media por modelo x papel x effort (USD/rodada,
                                                        s/rodada, turnos, USD/turno, s/turno) — a bancada para
                                                        decidir tier e effort por medida, nao por palpite
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


def por_modelo(linhas):
    """v13: medias por (modelo, papel, effort). Papel: juiz (rN), rubrica ou dupla. So linhas com usd medido;
    effort ausente (linhas anteriores a v13) sai como '-'. Qualidade NAO esta aqui: ela mora no ledger
    (veredictos) — este quadro responde quanto custa e quanto demora cada configuracao."""
    por = {}
    for l in linhas:
        d = parse(l)
        if not d or d['usd'] is None:
            continue
        kv = dict(re.findall(r'(\w+)=([^\s]+)', d['resto']))
        papel = 'juiz' if d['rod'].startswith('r') else d['rod']
        e = por.setdefault((d['modelo'], papel, kv.get('effort', '-')), {'n': 0, 'usd': 0.0, 's': 0.0, 'turnos': 0})
        e['n'] += 1
        e['usd'] += d['usd']
        e['s'] += d['s'] or 0.0
        e['turnos'] += int(kv['turnos']) if kv.get('turnos', '').isdigit() else 0
    out = ['%-28s %-8s %-7s %4s %8s %7s %8s %9s %8s'
           % ('modelo', 'papel', 'effort', 'n', 'USD/rod', 's/rod', 'turn/rod', 'USD/turno', 's/turno')]
    for k, e in sorted(por.items()):
        n, t = e['n'], e['turnos']
        out.append('%-28s %-8s %-7s %4d %8.2f %7.0f %8.1f %9.3f %8.1f'
                   % (k[0], k[1], k[2], n, e['usd'] / n, e['s'] / n, t / n,
                      (e['usd'] / t) if t else 0.0, (e['s'] / t) if t else 0.0))
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    a = sys.argv[1:]
    modelos = '--modelos' in a
    a = [x for x in a if x != '--modelos']
    arq = a[0] if a else PADRAO
    if not os.path.exists(arq):
        print('sem historico em', arq)
        sys.exit(1)
    with open(arq, encoding='utf-8', errors='replace') as f:
        linhas = f.readlines()
    print(por_modelo(linhas) if modelos else tabela(linhas))
