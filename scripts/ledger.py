# -*- coding: utf-8 -*-
"""Ledger da regua de escalada (v5, 06/09/2026): o que o juiz aprovou sozinho e o que esperou o dono.

Arquivo: ~/.claude/ocombo-ledger.jsonl (local, fora do canal). Uma linha JSON por evento:
  {"ts","instancia","tipo","texto","status"}  tipo: veredicto | escalada | sim
  - veredicto: gravado pelo juiz.py a cada rodada (APROVADO/AJUSTE/INDEFINIDO + USD)
  - escalada : passo que cai na REGUA (dinheiro, producao, apagar, terceiro, decisao) e espera o dono
  - sim      : o dono autorizou (a frase dele fica no texto; nunca inventar)

Uso:
  python ledger.py escalar   <instancia> <tipo-regua> "<o que precisa do dono>"
  python ledger.py sim       <instancia> "<frase do dono>" [--fecha <trecho>]
                             (fecha a escalada aberta mais recente; com --fecha, a mais recente cujo texto contem o trecho)
  python ledger.py pendentes [instancia]      exit 1 se ha escalada aberta (o juiz/hook usa como portao)
  python ledger.py resumo    [AAAA-MM-DD]     cupom do dia: ciclos, veredictos, USD, o que esperou o dono
  python ledger.py veredicto <instancia> <rodada> <veredicto> <usd>   (chamado pelo juiz.py)
Tipos da regua: dinheiro | producao | apagar | terceiro | decisao
"""
import json
import os
import sys
from datetime import datetime

LEDGER = os.environ.get('OCOMBO_LEDGER') or os.path.join(os.path.expanduser('~'), '.claude', 'ocombo-ledger.jsonl')
TIPOS_REGUA = ('dinheiro', 'producao', 'apagar', 'terceiro', 'decisao')
LARGURA = 40


def carregar(caminho=None):
    caminho = caminho or LEDGER
    if not os.path.exists(caminho):
        return []
    itens = []
    with open(caminho, encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    itens.append(json.loads(linha))
                except ValueError:
                    itens.append({'ts': '?', 'tipo': 'ilegivel', 'texto': linha[:80], 'instancia': '?'})
    return itens


def gravar(evento, caminho=None):
    caminho = caminho or LEDGER
    evento = dict(evento)
    evento.setdefault('ts', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, 'a', encoding='utf-8') as f:
        f.write(json.dumps(evento, ensure_ascii=False) + '\n')
    return evento


def pendentes(itens, instancia=None):
    """Escaladas sem 'sim' posterior na mesma instancia (logica pura)."""
    abertas = []
    for ev in itens:
        if instancia and ev.get('instancia') != instancia:
            continue
        if ev.get('tipo') == 'escalada':
            abertas.append(ev)
        elif ev.get('tipo') == 'sim' and abertas:
            # fecha a escalada aberta mais recente da mesma instancia; com 'fecha' (15/09/2026),
            # so a mais recente cujo texto contem o trecho - o sim LIFO ja fechou escalada errada
            # (incidente de 08/09/2026). Sem par = nao fecha nada.
            trecho = str(ev.get('fecha') or '').lower()
            for i in range(len(abertas) - 1, -1, -1):
                if abertas[i].get('instancia') != ev.get('instancia'):
                    continue
                if trecho and trecho not in str(abertas[i].get('texto') or '').lower():
                    continue
                abertas.pop(i)
                break
    return abertas


def resumo(itens, dia):
    """Cupom do dia (lista de linhas <= 40 colunas) a partir dos eventos com ts no dia AAAA-MM-DD."""
    do_dia = [ev for ev in itens if str(ev.get('ts', '')).startswith(dia)]
    linhas = ['=' * LARGURA, 'COMBO - RESUMO DO DIA'.center(LARGURA), dia.center(LARGURA), '=' * LARGURA]
    por_inst = {}
    for ev in do_dia:
        por_inst.setdefault(ev.get('instancia', '?'), []).append(ev)
    total_usd = 0.0
    n_rodadas = n_aprov = 0
    for inst, evs in sorted(por_inst.items()):
        vered = [e for e in evs if e.get('tipo') == 'veredicto']
        usd = sum(float(e.get('usd') or 0) for e in vered)
        total_usd += usd
        n_rodadas += len(vered)
        aprov = [e for e in vered if str(e.get('veredicto', '')).startswith('APROVADO')]
        n_aprov += len(aprov)
        ultimo = vered[-1].get('veredicto', '?') if vered else '-'
        linhas.append(os.path.basename(str(inst).rstrip('\\/'))[:LARGURA])
        linhas.append('  rodadas %d  final %s  USD %.2f' % (len(vered), ultimo, usd))
        for e in evs:
            if e.get('tipo') == 'escalada':
                linhas.append(('  ESPEROU VOCE [%s] %s' % (e.get('regua', '?'), e.get('texto', '')))[:LARGURA])
            elif e.get('tipo') == 'sim':
                linhas.append(('  SIM: %s' % e.get('texto', ''))[:LARGURA])
    linhas.append('-' * LARGURA)
    linhas.append('ciclos %d  rodadas %d  aprovadas %d' % (len(por_inst), n_rodadas, n_aprov))
    linhas.append('USD total %.2f' % total_usd)
    abertas = pendentes(itens)
    linhas.append('escaladas abertas: %d' % len(abertas))
    for e in abertas:
        linhas.append(('  ! [%s] %s: %s' % (e.get('regua', '?'), os.path.basename(str(e.get('instancia', '?')).rstrip('\\/')), e.get('texto', '')))[:LARGURA])
    linhas.append('=' * LARGURA)
    return linhas


def main(argv):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == 'escalar' and len(argv) >= 4:
        if argv[2] not in TIPOS_REGUA:
            print('tipo da regua invalido; use um de: ' + ', '.join(TIPOS_REGUA))
            return 2
        ev = gravar({'instancia': argv[1], 'tipo': 'escalada', 'regua': argv[2], 'texto': ' '.join(argv[3:])})
        print('escalada registrada: [%s] %s' % (ev['regua'], ev['texto']))
        return 0
    if cmd == 'sim' and len(argv) >= 3:
        resto, fecha = list(argv[2:]), ''
        if '--fecha' in resto:                      # qual escalada este sim fecha (trecho do texto)
            k = resto.index('--fecha')
            fecha = resto[k + 1] if k + 1 < len(resto) else ''
            del resto[k:k + 2]
        ev = {'instancia': argv[1], 'tipo': 'sim', 'texto': ' '.join(resto)}
        if fecha:
            ev['fecha'] = fecha
        ev = gravar(ev)
        print('sim registrado%s: %s' % ((' (fecha "%s")' % fecha) if fecha else '', ev['texto']))
        return 0
    if cmd == 'veredicto' and len(argv) >= 5:
        gravar({'instancia': argv[1], 'tipo': 'veredicto', 'rodada': argv[2], 'veredicto': argv[3], 'usd': argv[4]})
        return 0
    if cmd == 'pendentes':
        abertas = pendentes(carregar(), argv[1] if len(argv) > 1 else None)
        for e in abertas:
            print('[%s] %s: %s (%s)' % (e.get('regua'), e.get('instancia'), e.get('texto'), e.get('ts')))
        print('escaladas abertas: %d' % len(abertas))
        return 1 if abertas else 0
    if cmd == 'resumo':
        dia = argv[1] if len(argv) > 1 else datetime.now().strftime('%Y-%m-%d')
        print('\n'.join(resumo(carregar(), dia)))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
