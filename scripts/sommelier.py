# -*- coding: utf-8 -*-
"""SOMMELIER POR TAREFA (v11, 20/09/2026): qual modelo faz cada tarefa de um fan-out.

Ate a v10 o sommelier so escolhia modelo por PAPEL (grelha, executor, juiz). Faltava a outra metade:
quando o maestro abre um fan-out (Workflow ou Agent), quem OMITE `model` HERDA o modelo da sessao. Em
20/09/2026 isso pos 88 agentes de transcricao de pagina escaneada em Fable — trabalho mecanico no tier
mais caro da casa, 40 e tantas vezes. O dono parou a esteira: "chamar fable 40x e insanidade".

REGRAS (todas provadas em test_sommelier.py):
  R1  a CLASSE da tarefa decide o tier — nunca a sessao, nunca o habito;
  R2  LOTE NUNCA NO TOPO: LOTE_MIN ou mais agentes da mesma classe jamais rodam no tier de topo, em
      nenhuma classe, nenhum modo (o 10 tambem) e nenhuma sessao; classe de decisao em lote desce 1 tier;
  R3  quem confere e de tier DIFERENTE de quem fez (cross-model), acima quando o autor e barato;
  R4  modo alto compra CONFERENCIA e EFFORT, nunca tier de lote;
  R5  topo em lote a pedido do dono e regua de DINHEIRO: `--checar` sai 2 e a esteira para no ledger.

Uso (antes de TODO fan-out; a linha "Sommelier:" entra no ESTADO da instancia):
  python sommelier.py                                  tabela das classes
  python sommelier.py --tarefa transcricao --agentes 44
  python sommelier.py --plano "transcricao:44,conferencia:44,sintese:1" [--modo 7] [--tokens 60000,8000]
  python sommelier.py --checar "transcricao:44=fable"  exit 2 = recusa (regua)
  --descricao "o que os agentes vao fazer"   texto que o Jev le para escolher (sem ele: o exemplo da classe)
  --workflow   (com --plano/--tarefa) + a linha "Lancamento:" e o trecho JS {model, effort} por classe (04/10/2026)
  --autor TIER   autor da conferencia que ABRE o plano (--tarefa conferencia; --plano/--checar "conferencia:N,...");
                 nas outras conferencias o autor e a classe anterior, e --autor fora disso e erro de uso (04/10/2026)
O JEV ESCOLHE O MODELO E A FORCA (04/10/2026, jev_escolha.py) em --plano e --tarefa; as travas R2-R5 valem por cima;
sem Jev = regra fixa com o motivo escrito. Desligar: OCOMBO_JEV=off. O --checar segue contra a regra fixa.
O `alias` devolvido e o que o Workflow (`agent(prompt, {model, effort})`) e a ferramenta Agent (`model`) aceitam;
`modelo` e o id para `claude -p --model`. ESFORCO SO PELO WORKFLOW (04/10/2026): a ferramenta Agent NAO aceita effort;
classe com effort sai por agent() com o trecho do --workflow; Agent so com effort padrao (linha Lancamento no ESTADO). Sessao: --sessao ou OCOMBO_SESSAO (padrao: o tier de topo).
Saida: 0 ok | 1 erro de uso | 2 plano recusado. Detalhe e limites: references/sommelier.md.
"""
import json
import os
import sys

import jev_escolha
import modos

TIERS = ('haiku', 'sonnet', 'opus', 'fable')            # em ordem de preco; o ultimo e o TOPO
TOPO = TIERS[-1]
IDS = {'haiku': 'claude-haiku-4-5-20251001', 'sonnet': 'claude-sonnet-5-5', 'opus': 'claude-opus-5-5',
       'fable': 'claude-fable-5-1'}
# USD por 1M (input, output) — tabela de precos de 25/09/2026 (references/pesquisa-2026-10-02-v13.md).
# v13 (02/10/2026): Opus 5.5 custa 4 | 20 (o Opus 5 custava 5 | 25); Sonnet 5.5 e Haiku 4.5 mantiveram o preco.
# A geracao anterior (Opus 4.8 5 | 25, Sonnet 4.6 3 | 15) custa MAIS que a atual: voltar nela nao economiza.
PRECO = {'haiku': (1.0, 5.0), 'sonnet': (2.0, 10.0), 'opus': (4.0, 20.0), 'fable': (10.0, 50.0)}
LOTE_MIN = 3                                             # 3+ agentes da mesma classe = lote
SESSAO = 'sessao'                                        # tier "herda a sessao" (so para classe de decisao)

CLASSES = {
    'varredura':   {'tier': 'haiku', 'effort': 'low',
                    'exemplo': 'listar, grep, classificar arquivo, ler log, triagem de pasta'},
    'transcricao': {'tier': 'sonnet', 'effort': 'medium',
                    'exemplo': 'imagem/audio/PDF escaneado -> texto fiel; extracao estruturada'},
    'pesquisa':    {'tier': 'sonnet', 'effort': 'medium',
                    'exemplo': 'web, documentacao, leitura de fonte que volta resumo + fontes'},
    'redacao':     {'tier': 'sonnet', 'effort': 'medium',
                    'exemplo': 'capitulo, resumo de livro, documentacao, mensagem'},
    'conferencia': {'tier': None, 'effort': 'high',
                    'exemplo': 'segundo leitor cetico do trabalho de OUTRO agente (tier sai do autor)'},
    'julgamento':  {'tier': None, 'effort': None,
                    'exemplo': 'juiz de rubrica: quem manda e o modos.py (juiz e juiz_effort do modo)'},
    'codigo':      {'tier': SESSAO, 'effort': None,
                    'exemplo': 'implementacao com TDD; acoplado fica na sessao principal'},
    'sintese':     {'tier': SESSAO, 'effort': 'high',
                    'exemplo': 'arquitetura, decisao dificil, sintese final de um fan-out'},
}
MECANICAS = ('varredura', 'transcricao', 'pesquisa', 'redacao', 'conferencia')

_CONFERENTE = {'haiku': 'sonnet', 'sonnet': 'opus', 'opus': 'sonnet', 'fable': 'sonnet'}
_ALIAS_DO_ID = dict((v, k) for k, v in IDS.items())


def _tier(valor, o_que='tier'):
    t = str(valor).strip().lower()
    if t not in TIERS:
        raise ValueError('%s invalido: %r (use %s)' % (o_que, valor, ', '.join(TIERS)))
    return t


def conferente_de(autor):
    """R3: tier de quem confere o trabalho de `autor` — sempre outro, nunca o topo."""
    return _CONFERENTE[_tier(autor, 'autor')]


def _descer(tier):
    return TIERS[max(0, TIERS.index(tier) - 1)]


def escolher(classe, agentes=1, modo=0, sessao=None, autor=None, jev=None):
    """Modelo e effort para `agentes` tarefas da mesma `classe`. Levanta em vez de herdar em silencio.
    jev = {'tier', 'effort', 'p_tier', 'p_effort'} (jev_escolha.perguntar): o Jev escolhe modelo e forca (ordem do
    o dono, 04/10/2026) e as travas R2/R3/R4 e o juiz cross-model continuam valendo por cima."""
    if classe not in CLASSES:
        raise ValueError('classe de tarefa invalida: %r (use %s)' % (classe, ', '.join(sorted(CLASSES))))
    if isinstance(agentes, bool) or not isinstance(agentes, int) or agentes < 1:
        raise ValueError('agentes invalido: %r (inteiro >= 1)' % (agentes,))
    sessao = _tier(sessao or os.environ.get('OCOMBO_SESSAO') or TOPO, 'sessao')
    p = modos.perfil(modo)
    lote = agentes >= LOTE_MIN
    base = CLASSES[classe]
    effort = base['effort']

    if classe == 'julgamento':
        if p['juiz'] in _ALIAS_DO_ID:
            tier, effort = _ALIAS_DO_ID[p['juiz']], p['juiz_effort']
            motivo = 'juiz do modo %s (modos.py)' % p['chave']
        else:   # v15 (23/10/2026): juiz fora dos tiers Claude (agy:...) — quem o lanca e o juiz.py, nunca um subagente
            tier, effort = 'agy', None
            motivo = 'juiz do modo %s = %s pelo juiz.py (Antigravity CLI), nao e subagente' % (p['chave'], p['juiz'])
    elif classe == 'conferencia':
        tier = conferente_de(autor or 'sonnet')
        motivo = 'cross-model: confere trabalho feito em %s' % _tier(autor or 'sonnet', 'autor')
    elif base['tier'] == SESSAO:
        tier, motivo = sessao, 'classe de decisao: herda a sessao (%s)' % sessao
    else:
        tier, motivo = base['tier'], 'classe mecanica: tier da tabela'

    if jev:
        tier, effort = _tier(jev['tier']), jev['effort']
        motivo = 'Jev: %s (p=%.2f), forca %s (p=%.2f)' % (tier, jev['p_tier'], effort, jev['p_effort'])
        if classe == 'conferencia' and tier == _tier(autor or 'sonnet', 'autor'):     # R3 por cima do Jev
            tier = conferente_de(autor or 'sonnet')
            motivo += '; mesmo tier do autor -> %s (cross-model)' % tier
        if classe == 'julgamento' and tier == sessao:                                  # juiz != executor
            tier = _ALIAS_DO_ID[p['juiz']] if _ALIAS_DO_ID[p['juiz']] != sessao else conferente_de(sessao)
            motivo += '; juiz no tier da sessao -> %s (cross-model)' % tier

    if lote and tier == TOPO:                              # R2
        tier = _descer(tier)
        motivo += '; lote de %d nunca no topo -> %s' % (agentes, tier)

    chave = p['chave']
    if classe in MECANICAS and chave == 'f1':              # R4: o F1 compra tempo
        effort = 'low'
    elif classe == 'conferencia' and isinstance(chave, int) and chave >= 7:
        effort = 'xhigh'                                   # R4: modo alto compra effort, nao tier
    if effort is not None:
        modos.validar_effort(effort)
    return {'classe': classe, 'agentes': agentes, 'alias': tier, 'modelo': IDS.get(tier, p['juiz']), 'effort': effort,
            'lote': lote, 'motivo': motivo}


def _itens(texto):
    """'transcricao:44,conferencia:44=opus' -> [(classe, n, alias_forcado|None)]."""
    itens = []
    for bruto in str(texto or '').split(','):
        bruto = bruto.strip()
        if not bruto:
            continue
        corpo, _, forcado = bruto.partition('=')
        classe, sep, n = corpo.partition(':')
        classe, n = classe.strip(), n.strip()
        if not sep or not classe or not n.isdigit() or int(n) < 1:
            raise ValueError('item de plano invalido: %r (use classe:agentes[=alias])' % bruto)
        if classe not in CLASSES:
            raise ValueError('classe de tarefa invalida: %r (use %s)' % (classe, ', '.join(sorted(CLASSES))))
        itens.append((classe, int(n), _tier(forcado, 'alias') if forcado.strip() else None))
    if not itens:
        raise ValueError('plano vazio (use "classe:agentes,classe:agentes")')
    return itens


def _autor_inicial(itens, autor):
    """04/10/2026 (revisor): --autor era descartado em silencio fora do --tarefa conferencia. Ele so diz o autor da
    conferencia que ABRE o plano; nas outras o autor e a classe anterior, entao fora disso e erro de uso."""
    if not autor:
        return None
    if itens[0][0] != 'conferencia':
        raise ValueError('--autor so vale quando o plano abre com conferencia (aqui abre com %s; o autor das outras '
                         'conferencias e a classe anterior do plano)' % itens[0][0])
    return _tier(autor, 'autor')


def planejar(texto, modo=0, sessao=None, jev_transporte=None, descricao=None, autor=None):
    """Plano inteiro. A conferencia confere a classe ANTERIOR do plano (e dela que sai o autor); a que abre o plano
    confere `autor` (--autor). jev_transporte: com ele o Jev escolhe modelo e forca de cada classe (uma chamada por
    classe); sem Jev (falha, cota, rede) a classe cai na regra fixa e o motivo diz "regra fixa (sem Jev: ...)"."""
    itens = _itens(texto)
    escolhas, anterior = [], _autor_inicial(itens, autor)
    for classe, n, forcado in itens:
        j, falha = None, None
        if jev_transporte is not None and not forcado:
            try:
                j = jev_escolha.perguntar(classe, descricao or CLASSES[classe]['exemplo'], n, jev_transporte)
            except jev_escolha.SemJev as erro:
                falha = str(erro)
        e = escolher(classe, n, modo, sessao, autor=anterior, jev=j)
        if falha:
            e['motivo'] = 'regra fixa (sem Jev: %s); %s' % (falha, e['motivo'])
        e['autor'] = anterior if classe == 'conferencia' else None
        if forcado:
            e = dict(e, alias=forcado, modelo=IDS[forcado], motivo='FORCADO para %s' % forcado, forcado=True)
        escolhas.append(e)
        anterior = e['alias']
    return escolhas


def checar(texto, modo=0, sessao=None, autor=None):
    """(violacoes, avisos) de um plano com alias forcados. Violacao = exit 2 na CLI."""
    violacoes, avisos = [], []
    for e in planejar(texto, modo, sessao, autor=autor):
        if not e.get('forcado'):
            continue
        tabela = escolher(e['classe'], e['agentes'], modo, sessao, autor=e.get('autor'))['alias']
        if e['lote'] and e['alias'] == TOPO:
            violacoes.append('%s x%d em %s: lote no tier de topo e regua de DINHEIRO - so com o "sim" do '
                             'dono no ledger (a tabela manda %s)' % (e['classe'], e['agentes'], TOPO, tabela))
        elif e['classe'] == 'conferencia' and e.get('autor') == e['alias']:
            violacoes.append('conferencia em %s confere trabalho feito em %s: quebra o cross-model '
                             '(a tabela manda %s)' % (e['alias'], e['autor'], tabela))
        elif e['alias'] != tabela:
            avisos.append('%s x%d forcado para %s (a tabela manda %s)'
                          % (e['classe'], e['agentes'], e['alias'], tabela))
    return violacoes, avisos


def custo_relativo(escolhas):
    """Fracao do custo do MESMO plano todo no topo, supondo o mesmo volume por agente. Exato para
    qualquer mistura input/output enquanto a razao saida/entrada for igual em todo tier (testado);
    NAO cobre cache, cujo desconto varia por modelo."""
    total = sum(e['agentes'] for e in escolhas)
    return sum(e['agentes'] * PRECO[e['alias']][1] for e in escolhas) / (total * PRECO[TOPO][1])


def usd(escolhas, tokens_in, tokens_out):
    """USD de tabela para o volume INFORMADO por agente. Sem volume medido nao ha USD: nunca chute."""
    return sum(e['agentes'] * (tokens_in * PRECO[e['alias']][0] + tokens_out * PRECO[e['alias']][1]) / 1e6
               for e in escolhas)


def linha_estado(escolhas):
    """O que entra no ESTADO da instancia antes do fan-out (o plano e a fonte unica, nao a conversa)."""
    partes = ['%s x%d %s%s' % (e['classe'], e['agentes'], e['alias'], (' ' + e['effort']) if e['effort'] else '')
              for e in escolhas]
    return 'Sommelier: %s | %d%% do tudo-em-%s' % (' | '.join(partes), round(custo_relativo(escolhas) * 100), TOPO)


SEM_EFFORT = ('haiku',)      # Haiku 4.5 nao aceita effort (catalogo da metajev: a API da erro); references/sommelier.md


def _effort_lancado(e):
    """O effort que vai na chamada: o escolhido, menos em tier que nao aceita effort (04/10/2026, revisor)."""
    return None if e['alias'] in SEM_EFFORT else e['effort']


def opcoes_workflow(e):
    """{model, effort} do agent() do Workflow. Sem effort quando a classe roda no padrao (effort None) ou no Haiku."""
    o = {'model': e['alias']}
    if _effort_lancado(e) is not None:
        o['effort'] = _effort_lancado(e)
    return o


def lancar_por(e):
    """04/10/2026: a ferramenta Agent aceita model mas NAO effort. Effort escolhido = Workflow agent(); 'agent' so
    quando nao ha effort a levar (padrao, ou Haiku) - e isso vai declarado na linha Lancamento do ESTADO."""
    return 'agent' if _effort_lancado(e) is None else 'workflow'


def _chaves(escolhas):
    """classe, ou classe_2, classe_3... quando a mesma classe volta no plano."""
    vistas, chaves = {}, []
    for e in escolhas:
        vistas[e['classe']] = vistas.get(e['classe'], 0) + 1
        n = vistas[e['classe']]
        chaves.append(e['classe'] if n == 1 else '%s_%d' % (e['classe'], n))
    return chaves


def trecho_workflow(escolhas):
    """Pronto para colar no script do Workflow: o objeto e JSON valido (o teste le com json.loads)."""
    chaves = _chaves(escolhas)
    itens = ['  %s: %s' % (json.dumps(k), json.dumps(opcoes_workflow(e))) for k, e in zip(chaves, escolhas)]
    return '\n'.join(['// Workflow: cada agent() leva model E effort (a ferramenta Agent NAO aceita effort)',
                      'const SOMMELIER = {', ',\n'.join(itens), '}',
                      '// uso: agent(prompt, {...SOMMELIER[%s], label: "..."})' % json.dumps(chaves[0])])


def linha_lancamento(escolhas):
    """Entra no ESTADO junto da linha Sommelier: quem sai por Workflow e quem pode ir pela ferramenta Agent."""
    pares = list(zip(_chaves(escolhas), escolhas))
    wf = [k for k, e in pares if lancar_por(e) == 'workflow']
    ag = [k for k, e in pares if lancar_por(e) == 'agent']
    partes = (['Workflow agent() model+effort: ' + ', '.join(wf)] if wf else []) + \
        (['ferramenta Agent (effort padrao): ' + ', '.join(ag)] if ag else [])
    return 'Lancamento: ' + ' | '.join(partes)


def _imprimir(escolhas, tokens=None, workflow=False):
    for e in escolhas:
        print('  %-12s x%-4d %-7s %-7s %s' % (e['classe'], e['agentes'], e['alias'], e['effort'] or '-', e['motivo']))
    print(linha_estado(escolhas))
    if tokens:
        print('USD de tabela para %d in / %d out por agente: %.2f (todo no topo: %.2f) - estimativa, nao fatura'
              % (tokens[0], tokens[1], usd(escolhas, *tokens),
                 usd([dict(e, alias=TOPO) for e in escolhas], *tokens)))
    if workflow:
        print(linha_lancamento(escolhas))
        print(trecho_workflow(escolhas))


def _transporte_jev():
    """a ponte da skill jev (ssh vps jev raw); sem a skill, None e o plano sai na regra fixa"""
    j = jev_escolha._jev()
    return j.transporte_padrao if j else None


def main(argv):
    workflow = '--workflow' in argv                      # flag sem valor (04/10/2026)
    argv = [a for a in argv if a != '--workflow']
    if not argv:
        for nome in sorted(CLASSES):
            c = CLASSES[nome]
            print('  %-12s %-8s %-7s %s' % (nome, c['tier'] or 'derivado', c['effort'] or '-', c['exemplo']))
        print('lote = %d+ agentes da mesma classe; lote nunca em %s' % (LOTE_MIN, TOPO))
        return 0
    if argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    op = {'--agentes': '1', '--modo': None, '--sessao': None, '--autor': None, '--tokens': None,
          '--tarefa': None, '--plano': None, '--checar': None, '--descricao': None}
    i = 0
    while i < len(argv):
        if argv[i] not in op or i + 1 >= len(argv):
            raise ValueError('argumento invalido: %r (veja --help)' % argv[i])
        op[argv[i]] = argv[i + 1]
        i += 2
    modo = op['--modo'] if op['--modo'] is not None else (os.environ.get('OCOMBO_MODO') or 0)
    tokens = None
    if op['--tokens']:
        a, _, b = op['--tokens'].partition(',')
        if not (a.strip().isdigit() and b.strip().isdigit()):
            raise ValueError('--tokens invalido: %r (use entrada,saida por agente)' % op['--tokens'])
        tokens = (int(a), int(b))
    if op['--checar']:
        violacoes, avisos = checar(op['--checar'], modo, op['--sessao'], op['--autor'])
        _imprimir(planejar(op['--checar'], modo, op['--sessao'], autor=op['--autor']), tokens, workflow)
        for a in avisos:
            print('  aviso    ' + a)
        for v in violacoes:
            print('  RECUSADO ' + v)
        return 2 if violacoes else 0
    transporte = _transporte_jev() if jev_escolha.ligado() else None
    plano = op['--plano']
    if not plano and op['--tarefa']:
        if not op['--agentes'].isdigit():
            raise ValueError('--agentes invalido: %r' % op['--agentes'])
        plano = '%s:%s' % (op['--tarefa'], op['--agentes'])
    if plano:
        _imprimir(planejar(plano, modo, op['--sessao'], transporte, op['--descricao'], op['--autor']), tokens, workflow)
        return 0
    raise ValueError('diga --tarefa, --plano ou --checar (veja --help)')


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except ValueError as erro:
        print('erro: %s' % erro)
        sys.exit(1)
