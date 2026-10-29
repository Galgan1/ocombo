# -*- coding: utf-8 -*-
"""MODOS do combo (v9, 09/09/2026): um botao de 0 a 10 mais o perfil F1, sem tocar no piso.

O numero diz quanto o combo INVESTE acima do minimo seguro: 0 e o padrao de hoje, 10 e o "opala
queimador de tokens". F1 nao e um numero: e o eixo do TEMPO (paralelo, teto curto, juiz rapido).
Os dois queimam token; o 10 queima para ganhar CERTEZA, o F1 para ganhar VELOCIDADE.

REGRA DE OURO (nao negociavel): nenhum modo desliga portao. prova.bat, triagem, linter e a regua de
escalada rodam IGUAL do 0 ao 10 e no F1 — o que varia e o gasto ACIMA disso. `portoes()` prova.

Uso:
  OCOMBO_MODO=7            (ambiente; vale para o ciclo inteiro)
  python iniciar.py <pasta> --modo 7|f1
  python -c "import modos; print(modos.resumo(modos.perfil('f1')))"
  python iniciar.py <pasta> --modo 3+ [--escada]      (v13: dose colada ao modo; escada = sobe 1 degrau por AJUSTE)
Detalhe da tabela, o que cada degrau acrescenta e as fontes: references/modos.md.
"""
import os
import re

# Valores que a CLI aceita de verdade. MEDIDO em 09/09/2026 na build 2.1.263: `claude --effort banana`
# NAO falha — imprime "Warning: Unknown --effort value 'banana' — ignoring it and using the default
# effort. Valid values: low, medium, high, xhigh, max." e RODA a chamada (exit 0, USD 0,47 no teste).
# Portao silencioso: quem valida somos nos, antes de montar a linha de comando.
EFFORT_VALIDO = ('low', 'medium', 'high', 'xhigh', 'max')

# Cross-model e regra da casa (v2): o executor e Fable/Opus, o juiz e de outro tier.
# v13 (02/10/2026): ids da geracao atual (Sonnet 5.5, Opus 5.5), provados no custo.log em 01/10/2026;
# a geracao anterior (Sonnet 5, Opus 5, Opus 4.8, Sonnet 4.6) custa igual ou MAIS na tabela de precos.
# v15 (23/10/2026, H3 do dono): o juiz e o Antigravity CLI oficial (prefixo agy:, familia Gemini = cross-family com o
# executor Claude); a fila de cota em juiz.AGY_FILA_BASE cai para flash e, por ultimo, Sonnet via agy. Os ids claude-*
# continuam permitidos: OCOMBO_JUIZ_CLAUDE=1, a linha "Dados ... pessoais" do ESTADO (D2), dupla.py e rubrica.py.
# v16 (26/10/2026, o dono: "esqueça gemini. registre isto no processo."): o Gemini saiu do processo. O juiz de
# todos os perfis volta a ser o Sonnet 5.5 (tier diferente do executor Opus/Fable) e nenhum id agy: e permitido; na
# r1 de um ciclo de 26/10/2026 o argon estava sem cota e o flash teve a leitura negada em headless.
JUIZES_PERMITIDOS = ('claude-haiku-4-5-20251001', 'claude-sonnet-5-5', 'claude-opus-5-5')

# O PISO: identico em todos os modos. Se um perfil quiser mexer aqui, o teste reprova.
PORTOES = (
    'prova.bat da instancia (exit != 0 = AJUSTE sem juiz, 0 tokens)',
    'triagem deterministica da forma (0 tokens)',
    'linter de correcao qualidade.py antes do juiz (0 tokens)',
    'regua de escalada: dinheiro, producao, apagar, terceiro, decisao do dono',
    'carimbo aprovado.sha256 preso ao plano aprovado',
)

_BASE = {'juiz_effort': None, 'executor_effort': None, 'rubrica_previa': True, 'pesquisa': 0,
         'fan_out': None, 'fast': False, 'escalada': None, 'carimbo_entrega': False,
         'turbo_disponivel': False}


def _p(**kw):
    d = dict(_BASE)
    d.update(kw)
    return d


# dupla: 'nao' | 'fecho' (2o juiz so no carimbo da ENTREGA) | 'regua' (2o juiz so no passo que cai na regua de
# escalada: dinheiro, producao, apagar, terceiro, decisao do dono) | 'sempre' (toda rodada; nenhum perfil usa desde
# 29/10/2026, quando o dono consolidou o uso enxuto: a dupla concordava com o 1o juiz em 2 de cada 3 vezes).
PERFIS = {
    0: _p(apelido='padrao', juiz='claude-sonnet-5-5', rodadas=5, dupla='nao', paralelo=2, timeout=900,
          custo_relativo=10,
          resumo='o combo de hoje: juiz Sonnet 5.5 por diff, teto 5, rubrica criticada antes, sem dupla'),
    1: _p(apelido='conferido', juiz='claude-sonnet-5-5', rodadas=5, dupla='nao', paralelo=2, timeout=900,
          custo_relativo=12, carimbo_entrega=True,
          resumo='+ carimbo da ENTREGA: o juiz relê o que foi ENTREGUE, nao so o desenho'),
    2: _p(apelido='atento', juiz='claude-sonnet-5-5', juiz_effort='high', rodadas=5, dupla='nao', paralelo=2,
          timeout=900, custo_relativo=15, carimbo_entrega=True,
          resumo='+ juiz em effort high: le mais fundo antes de dar PASS'),
    3: _p(apelido='teimoso', juiz='claude-sonnet-5-5', juiz_effort='high', rodadas=7, dupla='nao', paralelo=2,
          timeout=900, custo_relativo=20, carimbo_entrega=True,
          resumo='+ teto de 7 rodadas: insiste em vez de entregar com pendencia'),
    4: _p(apelido='lido', juiz='claude-sonnet-5-5', juiz_effort='high', rodadas=7, dupla='nao', pesquisa=1,
          paralelo=3, timeout=900, custo_relativo=26, carimbo_entrega=True,
          resumo='+ 1 subagente de pesquisa auditada antes da grelha (fonte, nao memoria)'),
    5: _p(apelido='revisado', juiz='claude-sonnet-5-5', juiz_effort='high', rodadas=7, dupla='fecho',
          pesquisa=1, paralelo=3, timeout=900, custo_relativo=34, carimbo_entrega=True,
          resumo='+ dupla.py no fecho: 2o juiz sobre o mesmo estado, concordancia por criterio'),
    6: _p(apelido='forte', juiz='claude-sonnet-5-5', juiz_effort='high', executor_effort='high', rodadas=7,
          dupla='fecho', pesquisa=1, paralelo=3, timeout=900, custo_relativo=45, carimbo_entrega=True,
          resumo='+ executor em effort high: esforco alto dos dois lados'),
    7: _p(apelido='desconfiado', juiz='claude-sonnet-5-5', juiz_effort='high', executor_effort='high', rodadas=9,
          dupla='regua', pesquisa=2, paralelo=4, timeout=900, custo_relativo=60, carimbo_entrega=True,
          resumo='+ dupla nos passos da regua e teto 9: discordancia vira criterio ambiguo, nao "juiz ruim"'),
    8: _p(apelido='obcecado', juiz='claude-sonnet-5-5', juiz_effort='medium', executor_effort='high', rodadas=9,
          dupla='regua', pesquisa=2, paralelo=4, timeout=1200, custo_relativo=78, carimbo_entrega=True,
          resumo='+ timeout maior do juiz (1200 s); juiz medium e executor high desde 29/10/2026 '
                 '(effort alto comprava espera, nao certeza: diagnostico interno de 29/10/2026)'),
    9: _p(apelido='esquadrao', juiz='claude-sonnet-5-5', juiz_effort='medium', executor_effort='high', rodadas=9,
          dupla='regua', pesquisa=3, paralelo=4, timeout=1200, fan_out='medium', custo_relativo=100,
          carimbo_entrega=True,
          resumo='+ fan-out de verificacao adversarial (workflow size medium, em levas de 4 agentes)'),
    10: _p(apelido='opala', juiz='claude-sonnet-5-5', juiz_effort='medium', executor_effort='high', rodadas=9,
           dupla='regua', pesquisa=4, paralelo=4, timeout=1800, fan_out='medium', custo_relativo=140,
           carimbo_entrega=True,
           resumo='o mais completo: pesquisa 4, timeout 1800 s, fan-out medium em levas de 4, dupla nos passos da '
                  'regua; juiz medium e executor high desde 29/10/2026. Use quando errar sai mais caro que gastar'),
    'f1': _p(apelido='formula 1', juiz='claude-sonnet-5-5', juiz_effort='low', rodadas=3, dupla='nao',
             rubrica_previa=False, pesquisa=1, paralelo=16, timeout=300, fan_out='medium', custo_relativo=55,
             turbo_disponivel=True,
             resumo='o eixo do tempo: tudo que e desacoplado sai em paralelo (stagger 0), teto 3, juiz Sonnet '
                    'em effort low com timeout de 5 min. Portoes iguais; o que cai e a espera, nao a prova'),
}


for _k, _v in PERFIS.items():
    _v['chave'] = _k          # o que o dono digita (0..10 | f1) — apelido e so o nome de guerra


def validar_effort(valor):
    """Devolve o valor se ele estiver na lista FECHADA; senao levanta. Exato: 'LOW ' e ' high' reprovam."""
    if valor not in EFFORT_VALIDO:
        raise ValueError('effort invalido: %r (a CLI aceita %s e IGNORA o resto com um aviso, '
                         'rodando assim mesmo)' % (valor, ', '.join(EFFORT_VALIDO)))
    return valor


APELIDOS = {'padrao': 0, 'padrão': 0, 'opala': 10, 'queimador': 10, 'f1': 'f1', 'formula1': 'f1',
            'formula-1': 'f1', 'formula 1': 'f1', 'fórmula 1': 'f1'}


def normalizar(valor):
    """'7' -> 7 · ' F1 ' -> 'f1' · 'opala' -> 10 · fora da escala -> ValueError."""
    if isinstance(valor, bool):
        raise ValueError('modo invalido: %r' % (valor,))
    if isinstance(valor, int):
        chave = valor
    else:
        t = str(valor).strip().lower()
        if t in APELIDOS:
            chave = APELIDOS[t]
        elif t.isdigit():
            chave = int(t)
        else:
            raise ValueError('modo invalido: %r (use 0..10, f1, padrao ou opala)' % (valor,))
    if chave not in PERFIS:
        raise ValueError('modo fora da escala: %r (use 0..10 ou f1)' % (valor,))
    return chave


def perfil(valor=None):
    """Perfil do modo pedido; sem argumento le OCOMBO_MODO; sem ambiente devolve o modo 0."""
    if valor is None:
        valor = os.environ.get('OCOMBO_MODO') or 0
    return PERFIS[normalizar(valor)]


TETO_ESCADA = 9   # a escada nunca chega sozinha ao 10 (opala) nem ao f1: esses so por pedido explicito
SUBIDA_MAXIMA = 3  # e nunca sobe mais que 3 degraus acima do modo de partida


def ajustar(valor, sufixo):
    """Dose POSTERIOR: '+' sobe 1, '-' desce 1, '+2'/'-3' sobem/descem N; resultado preso em 0..10.
    f1 nao tem vizinhos (e outro eixo): ajustar f1 levanta. Ex.: ajustar(3, '+2') -> 5."""
    chave = normalizar(valor)
    if chave == 'f1':
        raise ValueError('f1 e outro eixo (tempo): nao tem + nem -')
    t = str(sufixo).strip()
    if not t or t[0] not in '+-' or (len(t) > 1 and not t[1:].isdigit()):
        raise ValueError('dose invalida: %r (use +, -, +N ou -N)' % (sufixo,))
    passo = int(t[1:]) if len(t) > 1 else 1
    return max(0, min(10, chave + (passo if t[0] == '+' else -passo)))


def interpretar(texto):
    """v13: o que o dono digita depois de --modo, com a dose colada: '3' -> 3 · '3+' -> 4 · '3+2' -> 5 ·
    '7-' -> 6 · 'opala' -> 10 · 'f1' -> 'f1'. Apelido conhecido vale antes do sinal ('formula-1' e f1)."""
    t = str(texto).strip().lower()
    if t in APELIDOS or t.isdigit():
        return normalizar(t)
    m = re.match(r'^(\d+|[a-z][a-z0-9 ]*?)\s*([+-]\d*)$', t)
    if m:
        return ajustar(m.group(1), m.group(2))
    return normalizar(t)


def escalar(valor, falhas):
    """Escada: comeca barato e sobe um degrau por rodada REPROVADA (falhas = rodadas AJUSTE ate agora),
    ate TETO_ESCADA e ate SUBIDA_MAXIMA acima da partida. f1 e 10 ficam onde estao. Piso intacto."""
    chave = normalizar(valor)
    if chave == 'f1' or chave == 10 or falhas <= 0:
        return chave
    return min(chave + min(falhas, SUBIDA_MAXIMA), max(chave, TETO_ESCADA))


def portoes(_qualquer=None):
    """O piso, igual para todo modo. Existe para o teste provar que ninguem o move."""
    return PORTOES


def turbo(p):
    """F1 turbo: liga o fast mode do Opus (ate 2,5x mais rapido) e, com ele, a escalada de DINHEIRO —
    fast mode sai de usage credits, fora do limite da assinatura. Copia: a tabela nao muda."""
    if not p.get('turbo_disponivel'):
        raise ValueError('perfil %r nao tem turbo: fast mode e configuracao do Opus do executor, '
                         'nao roda em Sonnet nem Haiku' % p.get('apelido'))
    t = dict(p)
    t.update(fast=True, escalada='dinheiro',
             resumo=p['resumo'] + ' + fast mode do Opus (usage credits: precisa do "sim" do dono)')
    return t


def ambiente(p):
    """Variaveis que o EXECUTOR exporta para obedecer ao perfil (o juiz recebe tudo por argumento)."""
    amb = {'OCOMBO_MODO': str(p['chave'])}   # a CHAVE, nunca o apelido: 'conferido' nao volta por normalizar()
    if p['paralelo'] >= 16 and p['timeout'] <= 300:
        # F1: sem a espera que faz os irmaos do fan-out reaproveitarem o cache do primeiro (padrao 5000 ms).
        # Custa mais cache_write e devolve o tempo — que e exatamente a troca do F1.
        amb['CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS'] = '0'
    return amb


def resumo(p):
    """Uma linha para a conversa: apelido, juiz, teto, dupla e o resumo do perfil."""
    return ('modo %s | juiz %s%s | teto %d rodada(s) | dupla %s | paralelo %d | timeout %ds — %s'
            % (p['apelido'], p['juiz'], (' effort ' + p['juiz_effort']) if p['juiz_effort'] else '',
               p['rodadas'], p['dupla'], p['paralelo'], p['timeout'], p['resumo']))


def linha_estado(p, escada=False):
    """O que iniciar.py grava no ESTADO da instancia (o plano e a fonte unica, nao a conversa).
    v13: `escada: sim` na linha liga a escada para o juiz.py sem variavel de ambiente."""
    return ('Modo deste ciclo: %s (%s) | juiz %s%s | teto %d rodadas | dupla %s | paralelo %d%s'
            % (p['chave'], p['apelido'], p['juiz'], (' ' + p['juiz_effort']) if p['juiz_effort'] else '',
               p['rodadas'], p['dupla'], p['paralelo'], ' | escada: sim' if escada else ''))


if __name__ == '__main__':
    import sys
    a = sys.argv[1:]
    if a and a[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)
    if a:
        print(resumo(perfil(interpretar(a[0]))))   # v13: aceita a dose colada ('3+', '7-')
        sys.exit(0)
    for k in list(range(11)) + ['f1']:
        print('%-4s %s' % (k, resumo(PERFIS[k])))
