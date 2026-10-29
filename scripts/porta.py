# -*- coding: utf-8 -*-
"""PORTA de entrada do combo (v10, 10/09/2026): decide QUAIS laminas rodam neste pedido.

Nem todo pedido merece grelha. Reparo pontual com decisao ja fechada nao precisa de questionario —
precisa de teste vermelho, conserto e juiz. Esta porta decide isso por FATOS declarados (nao por
sensacao), imprime o bloco que vai para o ESTADO da instancia e sai 0. O que ela NUNCA faz: dispensar
a grelha quando o pedido toca a regua de escalada (dinheiro, producao, apagar, terceiro, decisao do
dono) — nem com ordem explicita (exit 2).

Uso:
  python porta.py --pedido "conserta o acento do relatorio" --reparo --arquivos 1
  python porta.py --pedido "sobe o painel novo na VPS" --novo --regua producao
  python porta.py --pedido "..." --forcar grelha|sem-grelha [--json]

Fatos (o maestro declara; sem flag, a palavra do pedido pre-preenche e o motivo diz isso):
  --novo / --reparo · --arquivos N · --regua a,b · --decisoes-abertas N · --criterio-de-pronto sim|nao
"""
import argparse
import json
import sys
import unicodedata

# Escopo acima deste tamanho deixa de ser reparo: alguem tem de desenhar antes de escrever.
LIMIAR_ARQUIVOS = 5
REGUA = ('dinheiro', 'producao', 'apagar', 'terceiro', 'decisao')

# Palavra no pedido -> fato que ela levanta. Pre-preenche; flag explicita do maestro vence.
GATILHOS = {
    'novo': (('criar', 'novo', 'nova', 'do zero', 'reescrever', 'migrar', 'refazer', 'projeto'), None),
    'regua:dinheiro': (('pagar', 'contratar', 'comprar', 'licenca', 'assinatura', 'plano'), 'dinheiro'),
    'regua:producao': (('publicar', 'deploy', 'subir', 'no ar', 'producao', 'restart', 'nginx', 'cron'), 'producao'),
    'regua:apagar': (('apagar', 'deletar', 'remover tudo', 'drop', 'force'), 'apagar'),
    'regua:terceiro': (('enviar', 'mandar', 'postar', 'e-mail', 'email', 'grupo', 'whatsapp'), 'terceiro'),
}


def _sem_acento(t):
    n = unicodedata.normalize('NFD', t or '')
    return ''.join(c for c in n if unicodedata.category(c) != 'Mn').lower()


def pistas(pedido):
    """Fatos que as palavras do pedido levantam: {'novo': bool, 'regua': [..]}. Nunca decide sozinho."""
    t = _sem_acento(pedido)
    novo = False
    regua = []
    for chave, (palavras, tipo) in GATILHOS.items():
        achou = any(p in t for p in palavras)
        if not achou:
            continue
        if chave == 'novo':
            novo = True
        elif tipo and tipo not in regua:
            regua.append(tipo)
    return {'novo': novo, 'regua': sorted(regua)}


def decidir(pedido='', novo=None, reparo=False, arquivos=None, regua=None, decisoes_abertas=0,
            criterio_de_pronto=True, forcar=None):
    """Decide a porta. Devolve dict com grelha (bool), motivos, laminas, papeis e o bloco do ESTADO.

    Regra de ouro: `forcar='sem-grelha'` NAO vale quando a regua e tocada — a porta recusa (valida=False).
    """
    p = pistas(pedido)
    novo = p['novo'] if novo is None else bool(novo)
    regua = sorted(set(list(regua or []) + p['regua']))
    invalidos = [r for r in regua if r not in REGUA]
    arquivos = -1 if arquivos is None else int(arquivos)

    obriga = []
    if forcar == 'grelha':
        obriga.append('ordem explicita do maestro (--forcar grelha)')
    if novo and not reparo:
        obriga.append('peca nova (nao e reparo em coisa que ja existe)')
    if regua:
        obriga.append('toca a regua de escalada: ' + ', '.join(regua))
    if arquivos >= LIMIAR_ARQUIVOS:
        obriga.append('escopo largo (%d arquivos >= %d)' % (arquivos, LIMIAR_ARQUIVOS))
    if not criterio_de_pronto:
        obriga.append('pedido sem criterio de pronto (nao da para escrever RUBRICA binaria)')
    if int(decisoes_abertas) > 0:
        obriga.append('%d decisao(oes) em aberto para o dono ou para o combo' % int(decisoes_abertas))

    recusa = None
    if forcar == 'sem-grelha' and regua:
        recusa = ('NAO dispenso a grelha: o pedido toca a regua (%s). Portao nao se desliga por ordem.'
                  % ', '.join(regua))
    if invalidos:
        recusa = 'tipo de regua desconhecido: ' + ', '.join(invalidos)

    if recusa:
        grelha = True
    elif forcar == 'sem-grelha':
        grelha = False
    else:
        grelha = bool(obriga)

    dispensa = []
    if not grelha:
        dispensa.append('reparo pontual' if reparo else 'escopo fechado')
        if 0 <= arquivos < LIMIAR_ARQUIVOS:
            dispensa.append('%d arquivo(s)' % arquivos)
        if int(decisoes_abertas) == 0:
            dispensa.append('decisoes ja fechadas (H1..Hn valem como herdadas)')
        dispensa.append('sem regua tocada')
        if forcar == 'sem-grelha':
            dispensa.append('ordem explicita do maestro (--forcar sem-grelha)')
            if obriga:  # a ordem venceu fatos que pediam grelha: fica escrito no ESTADO
                dispensa.append('apesar de: ' + '; '.join(obriga))

    laminas = (['grelha'] if grelha else []) + ['executor', 'juiz']
    if 'producao' in regua:
        laminas.append('producao')
    papeis = {
        'grelha': 'ocombo-grelha' if grelha else 'dispensada',
        'executor': 'ocombo-executor',
        'juiz': 'ocombo-juiz (cross-model, tier diferente do executor)',
    }
    motivos = obriga if grelha else dispensa
    return {'grelha': grelha, 'motivos': motivos, 'laminas': laminas, 'papeis': papeis,
            'regua': regua, 'recusa': recusa, 'valida': recusa is None,
            'estado': bloco_estado(grelha, motivos, laminas, papeis)}


def bloco_estado(grelha, motivos, laminas, papeis):
    """As tres linhas que o ESTADO da instancia passa a ter (o juiz cobra isso em C0)."""
    return '\n'.join([
        'Porta: GRELHA=%s - %s' % ('SIM' if grelha else 'NAO', '; '.join(motivos)),
        'Laminas: ' + ' -> '.join(laminas),
        'Papeis: grelha=%s | executor=%s | juiz=%s' % (papeis['grelha'], papeis['executor'], papeis['juiz']),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description='Porta de entrada do combo: quais laminas rodam.')
    ap.add_argument('--pedido', default='')
    ap.add_argument('--novo', action='store_true')
    ap.add_argument('--reparo', action='store_true')
    ap.add_argument('--arquivos', type=int, default=None)
    ap.add_argument('--regua', default='')
    ap.add_argument('--decisoes-abertas', type=int, default=0)
    ap.add_argument('--criterio-de-pronto', choices=('sim', 'nao'), default='sim')
    ap.add_argument('--forcar', choices=('grelha', 'sem-grelha'), default=None)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    d = decidir(pedido=a.pedido, novo=True if a.novo else None, reparo=a.reparo, arquivos=a.arquivos,
                regua=[r.strip() for r in a.regua.split(',') if r.strip()],
                decisoes_abertas=a.decisoes_abertas, criterio_de_pronto=(a.criterio_de_pronto == 'sim'),
                forcar=a.forcar)
    if a.json:
        print(json.dumps(d, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(d['estado'])
        if d['recusa']:
            print('RECUSA: ' + d['recusa'])
    return 0 if d['valida'] else 2


if __name__ == '__main__':
    sys.exit(main())
