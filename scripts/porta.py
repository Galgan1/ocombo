# -*- coding: utf-8 -*-
"""PORTA de entrada do combo (v10, 10/09/2026; v17, 07/11/2026): o TAMANHO do pedido, depois as laminas.

v17: antes de qualquer modo, a porta mede o tamanho. SIMPLES = um arquivo como alvo (URL ou nome), pedido curto,
sem lista de funcionalidades nem causa a descobrir, ate 2 arquivos na entrega, nenhuma decisao aberta e nada sem
volta (a regua, se tocada, e so producao com backup). Caminho SIMPLES: a sessao faz direto e sozinha, com o piso
(portao, um juiz sobre a entrega, sim no ledger antes do ar), sem dupla e sem Fable (decisao do dono, 08/11/2026),
e o modo pedido vale no maximo MODO_MAX_SIMPLES. Origem: 07/11/2026, "opala. crie um site... olamundo.html" abriu
4 pesquisas e a grelha para uma pagina de uma frase. Fontes: references/pesquisa-2026-11-07-v17.md.

NORMAL = todo o resto, como na v10: reparo pontual com decisao fechada dispensa a grelha; peca nova, escopo
largo, decisao aberta, pedido sem criterio de pronto ou regua tocada obrigam — e ordem nao dispensa a grelha
quando a regua e tocada (exit 2).

Uso:
  python porta.py --pedido "opala. crie um site... www.exemplo.com.br/olamundo.html" --modo opala
  python porta.py --pedido "conserta o acento do relatorio" --reparo --arquivos 1
  python porta.py --pedido "sobe o painel novo na VPS" --novo --regua producao
  python porta.py --pedido "..." --forcar grelha|sem-grelha [--simples] [--json]

Fatos (o maestro declara; sem flag, a palavra do pedido pre-preenche e o motivo diz isso):
  --novo / --reparo · --arquivos N (so a ENTREGA; andaime do combo nao conta) · --regua a,b ·
  --decisoes-abertas N · --criterio-de-pronto sim|nao · --simples (sem alvo escrito, ou palavra comum levantou regua sem volta) · --modo M
"""
import argparse
import json
import re
import sys
import unicodedata

import modos

# Escopo acima deste tamanho deixa de ser reparo: alguem tem de desenhar antes de escrever.
LIMIAR_ARQUIVOS = 5
REGUA = ('dinheiro', 'producao', 'apagar', 'terceiro', 'decisao')

# v17: tamanho do pedido.
LIMIAR_SIMPLES_ARQUIVOS = 2      # arquivos que a ENTREGA cria ou muda
LIMIAR_SIMPLES_PALAVRAS = 25     # palavras do pedido fora o alvo
MODO_MAX_SIMPLES = 1             # o modo compra certeza onde ha incerteza; pedido simples nao tem o que comprar
REGUA_COM_VOLTA = ('producao',)  # porta de duas maos: deploy com backup volta; dinheiro, apagar, terceiro e decisao nao
PALAVRAS_LARGAS = ('todos', 'todas', 'cada', 'inteiro', 'inteira', 'completo', 'completa', 'sistema', 'plataforma',
                   'app', 'aplicativo', 'bot', 'migrar', 'migre', 'refatorar', 'refatore', 'reescrever', 'reescreva',
                   'integrar', 'integre', 'pipeline', 'varios', 'varias', 'auditoria', 'revisao', 'redesenho', 'redesign')
PALAVRAS_DE_INCERTEZA = ('descubra', 'descobrir', 'investigue', 'investigar', 'diagnostique', 'diagnosticar', 'pesquise',
                         'pesquisar', 'compare', 'comparar', 'avalie', 'avaliar', 'analise', 'analisar')
SEPARADORES_DE_LISTA = 2         # 2+ virgulas ou "e" fora o alvo = lista de funcionalidades
NAO_ALVOS = ('node.js', 'vue.js', 'next.js', 'nuxt.js', 'react.js', 'three.js', 'd3.js', 'express.js', 'chart.js',
             'socket.io', 'asp.net', 'vb.net', 'e.g', 'i.e', 'p.ex')
TLDS = ('com', 'br', 'net', 'org', 'io', 'dev', 'gov', 'edu', 'info', 'biz', 'me', 'co', 'uk', 'us', 'ai', 'app', 'site',
        'online', 'tech', 'xyz')
# alvo = URL, dominio ou arquivo com extensao de letra; e-mail (depois de @) e numero de versao ficam fora
RE_ALVO = re.compile(r'(?<![@\w.-])(?:https?://)?[a-z0-9_-]+(?:\.[a-z0-9_-]+)*\.[a-z][a-z0-9]*(?:/[^\s,;]*)?', re.I)

# Palavra no pedido -> fato que ela levanta. Pre-preenche; flag explicita do maestro vence.
# v17: a regua casa palavra inteira, com o imperativo (o dono fala "paga", "apague", "manda"), fora o texto do alvo.
GATILHOS = {
    'novo': (('criar', 'novo', 'nova', 'do zero', 'reescrever', 'migrar', 'refazer', 'projeto'), None),
    'regua:dinheiro': (('pagar', 'paga', 'pague', 'paguei', 'pagamento', 'pagamentos', 'contratar', 'contrata', 'contrate',
                        'comprar', 'compre', 'comprei', 'licenca', 'assinatura', 'plano', 'transferir', 'transfira', 'pix'),
                       'dinheiro'),
    'regua:producao': (('publicar', 'publica', 'publique', 'deploy', 'deployar', 'subir', 'sobe', 'suba', 'no ar', 'producao',
                        'restart', 'reiniciar', 'reinicia', 'reinicie', 'nginx', 'cron', 'crontab'), 'producao'),
    'regua:apagar': (('apagar', 'apaga', 'apague', 'apaguei', 'deletar', 'deleta', 'delete', 'excluir', 'exclua', 'exclui',
                      'remover tudo', 'rm -rf', 'drop', 'force'), 'apagar'),
    'regua:terceiro': (('enviar', 'envia', 'envie', 'enviei', 'mandar', 'manda', 'mande', 'mandei', 'postar', 'posta', 'poste',
                        'postei', 'e-mail', 'email', 'emails', 'grupo', 'grupos', 'whatsapp', 'telegram'), 'terceiro'),
}


def _sem_acento(t):
    n = unicodedata.normalize('NFD', t or '')
    return ''.join(c for c in n if unicodedata.category(c) != 'Mn').lower()


def pistas(pedido):
    """Fatos que as palavras do pedido levantam: {'novo': bool, 'regua': [..]}. Nunca decide sozinho."""
    t = RE_ALVO.sub(' ', _sem_acento(pedido))
    novo = False
    regua = []
    for chave, (palavras, tipo) in GATILHOS.items():
        if chave == 'novo':
            novo = any(p in t for p in palavras)
        elif tipo not in regua and any(re.search(r'\b' + re.escape(p) + r'\b', t) for p in palavras):
            regua.append(tipo)
    return {'novo': novo, 'regua': sorted(regua)}


def alvos(pedido):
    """Alvos do pedido (URL, dominio, arquivo), sem repeticao, na ordem em que aparecem."""
    vistos = []
    for m in RE_ALVO.finditer(_sem_acento(pedido)):
        a = m.group(0).rstrip('.,;:)!?').rstrip('/')
        if a not in NAO_ALVOS and a not in vistos:
            vistos.append(a)
    return vistos


def _e_arquivo(alvo):
    """Alvo concreto e UM arquivo: URL cujo ultimo trecho tem extensao, ou nome de arquivo solto. Dominio e secao nao."""
    sem_esquema = alvo.split('://')[-1]
    if '/' in sem_esquema:
        return '.' in sem_esquema.rsplit('/', 1)[-1]
    return sem_esquema.rsplit('.', 1)[-1] not in TLDS


def tamanho(pedido='', simples=None, arquivos=-1, regua=(), decisoes_abertas=0, criterio_de_pronto=True,
            forcar=None):
    """v17: ('SIMPLES'|'NORMAL', motivos, aviso). Pista do texto: 1 alvo concreto, ate LIMIAR_SIMPLES_PALAVRAS
    palavras fora o alvo, nenhuma palavra de escopo largo. `simples` (do maestro) substitui a pista. Por cima dos
    dois valem os fatos: ordem de grelha e regua sem volta empurram sempre; arquivos, decisao aberta e falta de
    pronto empurram e, se a pista dizia SIMPLES, deixam o AVISO (o vies medido e contar andaime como entrega)."""
    achados = alvos(pedido)
    resto = RE_ALVO.sub(' ', _sem_acento(pedido))
    toks = re.findall(r'[a-z0-9]+', resto)
    largas = sorted(set(toks) & set(PALAVRAS_LARGAS))
    duvidas = sorted(set(toks) & set(PALAVRAS_DE_INCERTEZA)) + (['por que'] if re.search(r'\bpor que\b', resto) else [])
    separadores = resto.count(',') + len(re.findall(r'\be\b', resto))
    arquivo = len(achados) == 1 and _e_arquivo(achados[0])
    pista = (arquivo and len(toks) <= LIMIAR_SIMPLES_PALAVRAS and not largas and not duvidas
             and separadores < SEPARADORES_DE_LISTA)
    candidato = pista if simples is None else bool(simples)
    duros, moles = [], []
    if forcar == 'grelha':
        duros.append('ordem explicita do maestro (--forcar grelha)')
    sem_volta = [r for r in regua if r not in REGUA_COM_VOLTA]
    if sem_volta:
        duros.append('regua sem volta: ' + ', '.join(sem_volta))
    if arquivos > LIMIAR_SIMPLES_ARQUIVOS:
        moles.append('%d arquivos na entrega (> %d)' % (arquivos, LIMIAR_SIMPLES_ARQUIVOS))
    if int(decisoes_abertas) > 0:
        moles.append('%d decisao(oes) em aberto' % int(decisoes_abertas))
    if not criterio_de_pronto:
        moles.append('sem criterio de pronto declarado')
    if candidato and not duros and not moles:
        if simples is None:
            return 'SIMPLES', ['1 alvo: %s; %d palavras' % (achados[0], len(toks))], None
        return 'SIMPLES', ['declarado pelo maestro (--simples)'], None
    motivos = duros + moles
    if not candidato:
        if simples is False:
            motivos.append('declarado NORMAL pelo maestro')
        elif len(achados) != 1:
            motivos.append('%d alvos concretos no pedido (SIMPLES pede 1: URL ou arquivo)' % len(achados))
        elif not arquivo:
            motivos.append('alvo sem arquivo (dominio ou secao do site): ' + achados[0])
        elif largas:
            motivos.append('escopo largo no pedido: ' + ', '.join(largas))
        elif duvidas:
            motivos.append('causa a descobrir no pedido: ' + ', '.join(duvidas))
        elif separadores >= SEPARADORES_DE_LISTA:
            motivos.append('lista de funcionalidades no pedido (%d separadores)' % separadores)
        else:
            motivos.append('pedido longo (%d palavras > %d)' % (len(toks), LIMIAR_SIMPLES_PALAVRAS))
    aviso = None
    if candidato and moles and not duros:
        exemplo = achados[0] if achados else 'o alvo'
        aviso = ('o pedido tem cara de SIMPLES e so fatos declarados o levaram a NORMAL (%s). Confira antes de seguir: '
                 'arquivo conta so o que a ENTREGA cria ou muda (andaime do combo nao conta) e o pronto de um alvo so '
                 'cabe numa linha (ex.: "%s responde e mostra o pedido"). Fato errado: rode a porta de novo.'
                 % ('; '.join(moles), exemplo))
    return 'NORMAL', motivos, aviso


def modo_efetivo(modo, tam):
    """O tamanho e o teto do modo: SIMPLES vale no maximo MODO_MAX_SIMPLES; f1 (eixo do tempo) passa como esta."""
    chave = modos.normalizar(modo) if isinstance(modo, int) else modos.interpretar(modo)
    if tam == 'SIMPLES' and chave != 'f1':
        return min(chave, MODO_MAX_SIMPLES)
    return chave


def decidir(pedido='', novo=None, reparo=False, arquivos=None, regua=None, decisoes_abertas=0,
            criterio_de_pronto=True, forcar=None, modo=None, simples=None):
    """Decide a porta. Devolve dict com tamanho, grelha (bool), motivos, laminas, papeis, modo_efetivo e o bloco do
    ESTADO (3 linhas).

    Regra de ouro: `forcar='sem-grelha'` NAO vale quando a regua e tocada num pedido NORMAL — a porta recusa
    (valida=False). No SIMPLES a grelha cai pelo tamanho, e a regua de producao continua no ledger.
    """
    p = pistas(pedido)
    novo = p['novo'] if novo is None else bool(novo)
    declarada = list(regua or [])
    # --simples e o maestro dizendo que a palavra era comum ("plano de aula"): cai a pista sem volta, nunca a declarada
    descartadas = [r for r in p['regua'] if simples and r not in REGUA_COM_VOLTA and r not in declarada]
    regua = sorted(set(declarada + [r for r in p['regua'] if r not in descartadas]))
    invalidos = [r for r in regua if r not in REGUA]
    arquivos = -1 if arquivos is None else int(arquivos)

    def medir(lista):
        return tamanho(pedido, simples, arquivos, lista, decisoes_abertas, criterio_de_pronto, forcar)

    tam, motivos_tam, aviso = medir(regua)
    if descartadas:
        aviso = ('--simples descartou a pista de regua (%s): confira que o pedido nao mexe em dinheiro, apagar, terceiro '
                 'nem decisao do dono; se mexer, tire o --simples.' % ', '.join(descartadas))
    elif tam == 'NORMAL' and not aviso and p['regua'] and medir(declarada)[0] == 'SIMPLES':
        aviso = ('a regua %s veio so de palavra do pedido. Palavra comum (ex.: "plano de aula", "grupo de botoes"): rode '
                 'com --simples. Se o pedido mexe mesmo nisso, siga no NORMAL.' % ', '.join(p['regua']))
    efetivo, erro_modo = None, None
    if modo is not None:
        try:
            efetivo = modo_efetivo(modo, tam)
        except ValueError as e:
            erro_modo = str(e)
    comum = {'tamanho': tam, 'alvos': alvos(pedido), 'aviso': aviso, 'modo_efetivo': efetivo, 'regua': regua}

    if tam == 'SIMPLES' and not erro_modo:
        motivos = ['tamanho SIMPLES (%s)' % '; '.join(motivos_tam)]
        if modo is not None:
            motivos.append('modo pedido %s vale %s' % (modo_efetivo(modo, 'NORMAL'), efetivo))
        if regua:
            motivos.append('regua %s: ledger.py escalar e o sim do dono antes do ar' % ', '.join(regua))
        laminas = ['executor', 'juiz'] + (['producao'] if 'producao' in regua else [])
        papeis = {'grelha': 'dispensada (SIMPLES)', 'executor': 'sessao principal, direto (sem subagente)',
                  'juiz': 'juiz.py sobre a entrega (cross-model, tier diferente do executor; unico fecho do SIMPLES)'}
        return dict(comum, grelha=False, motivos=motivos, laminas=laminas, papeis=papeis, recusa=None, valida=True,
                    estado=bloco_estado(False, motivos, laminas, papeis))

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
    if erro_modo:
        recusa = erro_modo

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
    motivos = ['tamanho %s (%s)' % (tam, '; '.join(motivos_tam))] + (obriga if grelha else dispensa)
    return dict(comum, grelha=grelha, motivos=motivos, laminas=laminas, papeis=papeis, recusa=recusa,
                valida=recusa is None, estado=bloco_estado(grelha, motivos, laminas, papeis))


def bloco_estado(grelha, motivos, laminas, papeis):
    """As tres linhas que o ESTADO da instancia passa a ter (o juiz cobra isso em C0)."""
    return '\n'.join([
        'Porta: GRELHA=%s - %s' % ('SIM' if grelha else 'NAO', '; '.join(motivos)),
        'Laminas: ' + ' -> '.join(laminas),
        'Papeis: grelha=%s | executor=%s | juiz=%s' % (papeis['grelha'], papeis['executor'], papeis['juiz']),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description='Porta de entrada do combo: o tamanho do pedido, depois as laminas.')
    ap.add_argument('--pedido', default='')
    ap.add_argument('--novo', action='store_true')
    ap.add_argument('--reparo', action='store_true')
    ap.add_argument('--arquivos', type=int, default=None)
    ap.add_argument('--regua', default='')
    ap.add_argument('--decisoes-abertas', type=int, default=0)
    ap.add_argument('--criterio-de-pronto', choices=('sim', 'nao'), default='sim')
    ap.add_argument('--forcar', choices=('grelha', 'sem-grelha'), default=None)
    ap.add_argument('--simples', action='store_true')
    ap.add_argument('--modo', default=None)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    d = decidir(pedido=a.pedido, novo=True if a.novo else None, reparo=a.reparo, arquivos=a.arquivos,
                regua=[r.strip() for r in a.regua.split(',') if r.strip()],
                decisoes_abertas=a.decisoes_abertas, criterio_de_pronto=(a.criterio_de_pronto == 'sim'),
                forcar=a.forcar, modo=a.modo, simples=True if a.simples else None)
    if a.json:
        print(json.dumps(d, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(d['estado'])
        if d['tamanho'] == 'SIMPLES' and d['valida']:
            print('Caminho SIMPLES: a sessao faz direto e sozinha (portao do projeto, um juiz sobre a entrega%s; '
                  'sem dupla e sem Fable, decisao do dono de 08/11/2026)%s.'
                  % (', sim no ledger antes do ar' if 'producao' in d['regua'] else '',
                     '; abra a instancia com --modo %s' % d['modo_efetivo'] if d['modo_efetivo'] is not None else ''))
            print('Confira: uma entrega so, sem lista de funcionalidades nem causa a descobrir; se for maior, --forcar grelha.')
        if d['aviso']:
            print('AVISO: ' + d['aviso'])
        if d['recusa']:
            print('RECUSA: ' + d['recusa'])
    return 0 if d['valida'] else 2


if __name__ == '__main__':
    sys.exit(main())
