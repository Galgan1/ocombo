# -*- coding: utf-8 -*-
"""Juiz cross-model POR DIFF com custo medido (ocombo v2, 05/09/2026; v3 = triagem, manifesto, timeout,
historico global).

Uso:  python juiz.py <pasta_da_instancia> [modelo] [--timeout SEG] [--effort low|medium|high|xhigh|max]
      (padrao: claude-sonnet-5-5, 900 s, effort do modo; explicito > modo > padrao)

O que faz numa rodada:
  1. se existe prova.bat na instancia, roda ANTES: exit != 0 -> AJUSTE sem chamar o juiz (0 tokens);
  2. triagem DETERMINISTICA (triagem.py): ESTADO/RUBRICA numerada/REGRESSAO/SOLUCAO/caminhos citados —
     problema -> AJUSTE sem juiz (0 tokens);
  3. snapshot de solucao.txt em historico/solucao.rN.txt, delta.patch contra a rodada anterior e
     manifesto.txt (caminho, bytes, sha256) — identificadores leves para o juiz abrir so o que a SOLUCAO cita;
  4. rodada 1: o juiz le tudo; rodada N>1: julga SO os criterios FAIL da rodada anterior + regressao,
     lendo delta.patch primeiro ("A reviewer running in a fresh subagent context sees only the diff");
  5. chama `claude -p --output-format json` (sessao limpa) com TIMEOUT e 1 repeticao; estourou 2x ->
     veredicto.md "VEREDICTO: INDEFINIDO" + linha "timeout" (exit 3) — nunca AJUSTE (nao e culpa do executor);
  6. custo.log na instancia e ~/.claude/ocombo-custo.log (local, fora do canal) com o nome da instancia;
  7. garante veredicto.md (se o juiz nao gravou, usa o campo result) e copia para historico/veredicto.rN.md;
  8. v6 (06/09/2026): APROVADO grava aprovado.sha256 (hash do solucao.txt); `juiz.py --carimbo <pasta>` confere
     (exit 0 valido, 1 CADUCOU = plano mudou depois do carimbo, 2 nunca aprovado). O juiz para no bloco de
     CONFORMIDADE (C0) e marca o resto N/A; a rodada seguinte julga FAIL + N/A (pendentes_de).
Funcoes puras (delta, custo, linha_custo, veredicto, fails_de, pendentes_de, prompt, snapshot, carimbo) tem teste em test_juiz.py.
"""
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta

# v15 (23/10/2026, ciclo antigravity-juiz, H3 do dono): o Antigravity CLI oficial (`agy`) e o juiz do combo.
# Id com prefixo `agy:` = backend agy; sem prefixo = `claude -p` byte a byte como antes (OCOMBO_JUIZ_CLAUDE=1 volta a ele).
# v16 (26/10/2026, o dono: "esqueça gemini. registre isto no processo."): o Gemini saiu; o padrao volta ao Sonnet 5.5.
# O backend agy fica no codigo so para quem passar um id agy: EXPLICITO na linha de comando; modo e padrao nunca o usam.
MODELO_PADRAO = 'claude-sonnet-5-5'
MODELO_CLAUDE = 'claude-sonnet-5-5'          # o juiz de antes: OCOMBO_JUIZ_CLAUDE=1 ou linha "Dados ... pessoais" no ESTADO (D2)
TIMEOUT_PADRAO = 900
LIMITE_PROMPT = 24000                        # acima disso o prompt vai a historico/prompt.rN.txt (linha de comando do Windows: 32 k)
AGY_FILA_BASE = ('gemini-4-argon', 'gemini-3.8-flash', 'claude-sonnet-5-5')   # fallback de cota, nesta ordem, mesmo sufixo
AGY_WINGET = os.path.join(os.environ.get('LOCALAPPDATA') or '', 'Microsoft', 'WinGet', 'Packages',
                          'Google.AntigravityCLI_Microsoft.Winget.Source_8wekyb3d8bbwe', 'agy.exe')
COTA_CACHE = os.environ.get('OCOMBO_AGY_COTA') or os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
                                                               'ocombo', 'agy-cota.json')
TRIPWIRE_IGNORA = ('historico', '__pycache__', 'custo.log', 'delta.patch', 'manifesto.txt', 'aprovado.sha256',
                   'rubrica.critica.md', 'concordancia.md')
LOG_GLOBAL = os.environ.get('OCOMBO_CUSTO_GLOBAL') or os.path.join(os.path.expanduser('~'), '.claude', 'ocombo-custo.log')


def delta(antes, depois, nome_a, nome_b):
    """Diff unificado entre duas versoes; '' quando iguais."""
    if antes == depois:
        return ''
    linhas = difflib.unified_diff(antes.splitlines(True), depois.splitlines(True),
                                  fromfile=nome_a, tofile=nome_b, n=3)
    return ''.join(linhas)


def _ler(caminho):
    with open(caminho, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _gravar(caminho, texto):
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)


def rodada_atual(pasta):
    hist = os.path.join(pasta, 'historico')
    if not os.path.isdir(hist):
        return 0
    return len([a for a in os.listdir(hist) if re.match(r'solucao\.r\d+\.txt$', a)])


def snapshot(pasta):
    """Copia solucao.txt para historico/solucao.rN.txt; devolve N (numero da rodada)."""
    hist = os.path.join(pasta, 'historico')
    os.makedirs(hist, exist_ok=True)
    n = rodada_atual(pasta) + 1
    shutil.copyfile(os.path.join(pasta, 'solucao.txt'), os.path.join(hist, 'solucao.r%d.txt' % n))
    return n


def delta_da_rodada(pasta, n):
    """Escreve delta.patch (rodada n-1 -> n) e devolve o texto; '' na rodada 1."""
    if n <= 1:
        return ''
    hist = os.path.join(pasta, 'historico')
    a = _ler(os.path.join(hist, 'solucao.r%d.txt' % (n - 1)))
    b = _ler(os.path.join(hist, 'solucao.r%d.txt' % n))
    d = delta(a, b, 'solucao.r%d.txt' % (n - 1), 'solucao.r%d.txt' % n)
    _gravar(os.path.join(pasta, 'delta.patch'), d)
    return d


def custo(resp, rodada, modelo, effort=None):
    """Extrai usage/custo do JSON do `claude -p --output-format json`. Ausente -> None.
    v13: `effort` entra na linha (effort=high) para o custo_historico comparar effort x custo x tempo."""
    u = resp.get('usage') or {}
    extra = resp.get('_ocombo') or {}
    if backend_de(modelo) == 'agy' or extra:
        # v15: o JSON do agy traz tokens (input/output/thinking/cache_read) e segundos, nunca USD -> usd=n/d
        seg = resp.get('duration_seconds')
        usado = extra.get('modelo') or (modelo[4:] if modelo.startswith('agy:') else modelo)
        return {'rodada': rodada, 'modelo': 'agy:' + usado, 'effort': None, 'backend': 'agy',
                'input': u.get('input_tokens'), 'output': u.get('output_tokens'), 'thinking': u.get('thinking_tokens'),
                'cache_read': u.get('cache_read_tokens'), 'cache_write': None, 'usd': None,
                'segundos': float(seg) if seg is not None else None, 'turnos': resp.get('num_turns'),
                'fila': extra.get('fila', ''), 'tripwire': extra.get('tripwire')}
    usd = resp.get('total_cost_usd')
    ms = resp.get('duration_ms')
    return {
        'rodada': rodada, 'modelo': modelo, 'effort': effort,
        'input': u.get('input_tokens'), 'output': u.get('output_tokens'),
        'cache_read': u.get('cache_read_input_tokens'),
        'cache_write': u.get('cache_creation_input_tokens'),
        'usd': float(usd) if usd is not None else None,
        'segundos': (ms / 1000.0) if ms is not None else None,
        'turnos': resp.get('num_turns'),
    }


def linha_custo(c, rotulo=None, status='ok'):
    carimbo = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    rod = rotulo or ('r%d' % c['rodada'])
    if status != 'ok':
        return '%s %s %s %s' % (carimbo, rod, c['modelo'], status)
    if c.get('backend') == 'agy':
        return ('%s %s %s in=%s out=%s thinking=%s cache_read=%s usd=n/d s=%s turnos=%s fila=%s tripwire: %s violacoes'
                % (carimbo, rod, c['modelo'], c['input'], c['output'], c.get('thinking'), c['cache_read'], c['segundos'],
                   c['turnos'], c.get('fila') or '-', c.get('tripwire') if c.get('tripwire') is not None else '?'))
    if c['usd'] is None and c['input'] is None:
        return '%s %s %s sem usage' % (carimbo, rod, c['modelo'])
    return ('%s %s %s in=%s out=%s cache_read=%s cache_write=%s usd=%s s=%s turnos=%s%s'
            % (carimbo, rod, c['modelo'], c['input'], c['output'], c['cache_read'],
               c['cache_write'], c['usd'], c['segundos'], c['turnos'],
               (' effort=%s' % c['effort']) if c.get('effort') else ''))


def registrar_custo(pasta, c, rotulo=None, status='ok'):
    """Anexa a linha no custo.log da instancia e no historico global (com o nome da instancia)."""
    linha = linha_custo(c, rotulo, status)
    with open(os.path.join(pasta, 'custo.log'), 'a', encoding='utf-8', newline='\n') as f:
        f.write(linha + '\n')
    try:
        os.makedirs(os.path.dirname(LOG_GLOBAL), exist_ok=True)
        partes = linha.split(' ', 1)
        with open(LOG_GLOBAL, 'a', encoding='utf-8', newline='\n') as f:
            f.write('%s %s %s\n' % (partes[0], os.path.basename(os.path.abspath(pasta)), partes[1]))
    except OSError:
        pass
    return linha


def veredicto(texto):
    """Mesma regra do loop_run: negacao nunca aprova; linha canonica manda."""
    t = (texto or '').upper()
    m = re.search(r'VEREDICTO:\s*(APROVADO|AJUSTE|REPROVADO|INDEFINIDO)', t)
    if m:
        return {'APROVADO': 'APROVADO', 'INDEFINIDO': 'INDEFINIDO'}.get(m.group(1), 'AJUSTE')
    if 'REPROVADO' in t or 'NÃO APROVADO' in t or 'NAO APROVADO' in t:
        return 'AJUSTE'
    # Sem a linha canonica, um FAIL de criterio manda AJUSTE; "APROVADO" solto em prosa NUNCA aprova
    # (28/09/2026: o veredicto reprovou C0 e citava "apos o APROVADO r5 de la" - carimbo falso).
    if re.search(r'CRIT[EÉ]RIO\s+\S+:\s*FAIL', t) or 'AJUSTE' in t:
        return 'AJUSTE'
    return 'INDEFINIDO'


def sem_citacoes(linha):
    """Remove trechos entre aspas e crases: um FAIL citado ("FAIL sem segredo") nao e um FAIL do criterio
    (05/09/2026: a rodada 2 recebeu C3 como FAIL por causa disso)."""
    return re.sub(r'"[^"]*"|`[^`]*`|“[^”]*”', ' ', linha or '')


JANELA_ROTULO = 50  # o rotulo tem que vir ate 50 caracteres DEPOIS do criterio ("C7 — PASS", "C7 (...): FAIL")


def rotulo_do_criterio(linha):
    """(criterio, PASS|FAIL) da linha, ou None. Regra (05/09/2026, dois falsos FAIL num dia): fora de
    aspas/crases, o PRIMEIRO criterio cuja janela de 60 caracteres seguintes traz PASS/FAIL. Prosa como
    "os FAIL da r1 foram C9 e C7" nao conta (rotulo antes do criterio ou longe demais)."""
    limpa = sem_citacoes(linha)
    for m in re.finditer(r'\b(C\d+(?:\.\d+)?[a-c]?)\b', limpa):
        rot = re.search(r'\b(PASS|FAIL)\b', limpa[m.end():m.end() + JANELA_ROTULO])
        if rot:
            return m.group(1), rot.group(1)
    return None


RE_CANONICA = re.compile(r'^\s*CRITERIO\s+(C\d+(?:\.\d+)?[a-c]?)\s*:\s*(PASS|FAIL|N/A)\b', re.M | re.I)


RE_CRIT_RUBRICA = re.compile(r'^(C\d+(?:\.\d+)?[a-c]?)\.\s', re.M)


def criterios_da_rubrica(texto_solucao):
    """Ids dos critérios da seção RUBRICA do solucao.txt (a linha que começa com 'C<id>. '), na ordem."""
    m = re.search(r'^=== RUBRICA.*?$(.*?)(?=^===|\Z)', texto_solucao or '', re.S | re.M)
    return RE_CRIT_RUBRICA.findall(m.group(1)) if m else []


def pendentes_com_novos(texto_anterior, texto_solucao, historico=None):
    """O que a rodada por diff julga: FAIL e N/A do veredicto anterior e, no fim, os critérios da RUBRICA que NENHUM
    veredicto do histórico julgou (emenda no meio do ciclo). Sem isso, critério novo nunca era julgado (17/10/2026,
    ciclo de um video: C7b e C13b ficaram de fora da rodada 2). O histórico inteiro conta porque, na rodada por
    diff, o juiz pode imprimir só o que julgou. Sem veredicto anterior, a rodada é inteira."""
    if not texto_anterior:
        return []
    pend = pendentes_de(texto_anterior)
    julgados = set()
    for t in (historico or [texto_anterior]):
        julgados |= set(rotulos_canonicos(t))
    return pend + [c for c in criterios_da_rubrica(texto_solucao) if c not in julgados and c not in pend]


def historico_de_veredictos(pasta):
    """Os veredictos do juiz A gravados em historico/veredicto.rN.md, em ordem de rodada."""
    hist = os.path.join(pasta, 'historico')
    if not os.path.isdir(hist):
        return []
    nomes = sorted((n for n in os.listdir(hist) if re.fullmatch(r'veredicto\.r\d+\.md', n)),
                   key=lambda n: int(re.search(r'\d+', n).group(0)))
    return [_ler(os.path.join(hist, n)) for n in nomes]


def rotulos_canonicos(texto):
    """{'C9': 'FAIL', ...} das linhas canonicas `CRITERIO <id>: PASS|FAIL|N/A` que o prompt exige do juiz.
    Sem heuristica: e a mesma ideia da linha VEREDICTO. Vazio se o veredicto nao as trouxe."""
    saida = {}
    for m in RE_CANONICA.finditer(texto or ''):
        saida.setdefault(m.group(1), m.group(2).upper())
    return saida


def fails_de(texto_veredicto):
    """Criterios marcados FAIL no veredicto anterior (ordem de aparicao, sem repetir).
    Prefere as linhas canonicas; so cai na heuristica por linha se o veredicto nao as tiver."""
    can = rotulos_canonicos(texto_veredicto)
    if can:
        return [k for k, v in can.items() if v == 'FAIL']
    vistos, saida = set(), []
    for linha in (texto_veredicto or '').splitlines():
        r = rotulo_do_criterio(linha)
        if r and r[1] == 'FAIL' and r[0] not in vistos:
            vistos.add(r[0])
            saida.append(r[0])
    return saida


def pendentes_de(texto_veredicto):
    """v6: o que a rodada seguinte tem de julgar = FAIL + N/A (criterio que o juiz pulou por parar na
    CONFORMIDADE ou por ENTREGA ainda inexistente). Sem isso o N/A nunca mais seria julgado."""
    can = rotulos_canonicos(texto_veredicto)
    if can:
        return [k for k, v in can.items() if v in ('FAIL', 'N/A')]
    return fails_de(texto_veredicto)


def rodada_do_prompt(n, texto_anterior):
    """16/10/2026: rodada por diff so quando a anterior foi JULGADA (tem linhas CRITERIO). Rodadas que
    pararam na prova ou na triagem nao deixam veredicto do juiz; sem isso a seguinte "julgava so a
    regressao" e aprovava sem nunca ter lido a solucao."""
    if n <= 1 or not texto_anterior or not rotulos_canonicos(texto_anterior):
        return 1
    return n


CARIMBO = 'aprovado.sha256'


def sha256_de(caminho):
    with open(caminho, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def gravar_carimbo(pasta):
    """v6 (claudex-loop): APROVADO grava o sha256 do solucao.txt; mudou o plano, o carimbo caduca sozinho."""
    h = sha256_de(os.path.join(pasta, 'solucao.txt'))
    _gravar(os.path.join(pasta, CARIMBO), '%s  solucao.txt  %s\n' % (h, datetime.now().strftime('%Y-%m-%dT%H:%M:%S')))
    return h


def apagar_carimbo(pasta):
    cam = os.path.join(pasta, CARIMBO)
    if os.path.exists(cam):
        os.remove(cam)


def carimbo(pasta):
    """(estado, sha_atual, sha_gravado): estado = None (nunca aprovado) | 'APROVADO' | 'CADUCOU'."""
    cam = os.path.join(pasta, CARIMBO)
    sol = os.path.join(pasta, 'solucao.txt')
    atual = sha256_de(sol) if os.path.exists(sol) else ''
    if not os.path.exists(cam) or not atual:
        return None, atual, None
    gravado = _ler(cam).split()[0] if _ler(cam).strip() else ''
    return ('APROVADO' if gravado == atual else 'CADUCOU'), atual, gravado


CAVEMAN = {  # v8 (07/09/2026): a critica do juiz sai em modo caveman (regras da skill caveman, embutidas para rodar sem ela)
    'lite': 'ESTILO DA CRITICA (caveman lite): sem cortesia, sem hedge, sem narracao de ferramenta; frases inteiras. ',
    'full': ('ESTILO DA CRITICA (caveman full): frases curtas, sem artigos, sem cortesia, sem hedge, sem narracao de '
             'ferramenta, sem tabela decorativa, cada fato uma vez, sinonimo curto. NUNCA cortar nao/nunca/so/exceto. '
             'Numeros, nomes de arquivo, comandos e trechos de erro exatos. Portugues. '),
    'ultra': ('ESTILO DA CRITICA (caveman ultra): uma frase por criterio, sem artigos nem conjuncoes quando a causa fica '
              'clara, cada fato uma vez. NUNCA cortar nao/nunca/so/exceto. Numeros, nomes de arquivo, comandos e trechos '
              'de erro exatos. Portugues. '),
}
CAVEMAN_GUARDA = ('As linhas `CRITERIO <id>: ...` e `VEREDICTO: ...` ficam no formato exato. Em FAIL, o follow-up '
                  'cirurgico volta a prosa clara (ordem dos passos sem ambiguidade). ')


def nivel_caveman(valor=None):
    """Nivel do modo caveman da critica: OCOMBO_CAVEMAN=off|lite|full|ultra (padrao full; desconhecido = full)."""
    v = (os.environ.get('OCOMBO_CAVEMAN', 'full') if valor is None else valor).strip().lower()
    if v in ('off', '0', 'nao', 'no', 'false'):
        return 'off'
    return v if v in CAVEMAN else 'full'


def bloco_caveman(nivel=None):
    n = nivel_caveman(nivel)
    return '' if n == 'off' else CAVEMAN[n] + CAVEMAN_GUARDA


def prompt(rodada, fails, tem_delta, caveman=None, backend='claude'):
    # v15: o juiz agy NAO grava (write_file negado pela peca antigravity-juiz): o veredicto vem no texto da resposta.
    grava = ('Escreva veredicto.md nesta pasta, sobrescrevendo. Nao peca confirmacao. ' if backend != 'agy' else
             'Responda com o veredicto INTEIRO no texto da resposta: voce so le; nao grave arquivo nenhum nem rode comando '
             '(as travas negam e a rodada seria anulada). Arquivo citado fora das pastas liberadas: diga isso no criterio, '
             'nunca peca permissao. ')
    base = ('Voce e o VERIFIER cross-model do loop-agente. NAO execute a tarefa nem rode scripts; '
            'apenas JULGUE. Critica PASS/FAIL por criterio, NA ORDEM da rubrica, com motivo, ANTES do veredicto. '
            'O primeiro bloco da rubrica e CONFORMIDADE (C0: a SOLUCAO faz o que a TAREFA pede, no escopo, sem '
            'reabrir decisao herdada): se ele reprovar, PARE — marque os demais criterios como N/A e de AJUSTE; '
            'nao gaste leitura julgando a qualidade do que nao faz o que foi pedido. '
            'Depois da critica, um bloco com UMA linha por criterio da rubrica, exatamente no formato '
            '`CRITERIO <id>: PASS` ou `CRITERIO <id>: FAIL` (ou `CRITERIO <id>: N/A` quando a rubrica '
            'marca o criterio como ENTREGA ainda inexistente) — e o que a maquina le. '
            'Termine com UMA linha exatamente: VEREDICTO: APROVADO  ou  VEREDICTO: AJUSTE '
            '(nunca REPROVADO nem NAO APROVADO); se AJUSTE, follow-up cirurgico. '
            'manifesto.txt lista os arquivos da instancia (caminho, bytes, sha256): abra SO os que a '
            'SOLUCAO/ENTREGA citam ou que um criterio exige. ') + grava + bloco_caveman(caveman)
    if rodada <= 1 or not tem_delta:
        return base + 'Rodada 1: leia solucao.txt (tarefa + rubrica + solucao) por inteiro.'
    lista = ', '.join(fails) if fails else 'nenhum FAIL listado (julgue so a regressao)'
    return (base + 'Rodada %d: leia PRIMEIRO delta.patch (o que mudou desde a rodada anterior) e '
            'historico/veredicto.r%d.md (seu veredicto anterior). Julgue APENAS os criterios que '
            'estavam FAIL ou N/A (ainda nao julgados): %s — mais o criterio de REGRESSAO: o que estava PASS continua PASS '
            '(confira no delta se algo aprovado foi tocado; so releia solucao.txt nos trechos que o '
            'delta cita). Os demais criterios: repita o PASS anterior sem reler.'
            % (rodada, rodada - 1, lista))


def _claude():
    cmd = os.path.join(os.environ.get('APPDATA', ''), 'npm', 'claude.cmd')
    return cmd if os.path.exists(cmd) else (shutil.which('claude') or 'claude')


def argumentos_claude(modelo, effort=None, executavel=None):
    """v9: a linha do `claude -p` da rodada. SEM effort ela e byte a byte a de antes dos modos —
    e o que garante que quem nao escolhe modo continua no combo de sempre."""
    a = [executavel or _claude(), '-p', '--model', modelo, '--permission-mode', 'acceptEdits',
         '--output-format', 'json', '--no-session-persistence']
    if effort is not None:
        import modos
        a += ['--effort', modos.validar_effort(effort)]   # valor errado NUNCA vira argumento (a CLI o ignora calado)
    if os.environ.get('OCOMBO_SEM_MCP') == '1':   # v14: RAM curta -> o juiz nao carrega ElevenLabs/Playwright (~400 MB)
        a += ['--strict-mcp-config', '--mcp-config',
              os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'mcp-vazio.json')]
    return a


# --- v15: backend agy (Antigravity CLI oficial como juiz) -----------------------------------------------------------

_SUFIXOS = ('low', 'medium', 'high')


def backend_de(modelo):
    """'agy' para id com prefixo agy: (Antigravity CLI oficial); 'claude' para o resto (claude -p de sempre)."""
    return 'agy' if (modelo or '').startswith('agy:') else 'claude'


def _separar_sufixo(modelo_id):
    for s in _SUFIXOS:
        if modelo_id.endswith('-' + s):
            return modelo_id[:-len(s) - 1], s
    return modelo_id, None


def modelo_agy(base, effort=None):
    """Id do agy = familia + sufixo de esforco. O agy RECUSA --effort junto com o sufixo (medido 23/10/2026:
    "conflicts with --effort"), entao o esforco vive no id: low->-low, medium->-medium, high|xhigh|max|None->-high."""
    base, _ = _separar_sufixo(base)
    return '%s-%s' % (base, effort if effort in ('low', 'medium') else 'high')


def fila_agy(modelo_id):
    """Fila de fallback de cota: do modelo pedido em diante, na ordem AGY_FILA_BASE, com o MESMO sufixo.
    Modelo fora da base = fila de um so (nunca inventa modelo)."""
    base, sufixo = _separar_sufixo(modelo_id)
    if sufixo is None or base not in AGY_FILA_BASE:
        return [modelo_id]
    return ['%s-%s' % (b, sufixo) for b in AGY_FILA_BASE[AGY_FILA_BASE.index(base):]]


def _agy():
    return os.environ.get('OCOMBO_AGY') or shutil.which('agy') or AGY_WINGET


def argumentos_agy(modelo_id, prompt_texto, timeout, add_dirs=(), agente=None, executavel=None):
    """A linha do `agy -p`. NUNCA --dangerously-skip-permissions (as travas sao o settings.json + hook da peca
    antigravity-juiz) e NUNCA --effort (conflita com o sufixo do id). --disable-slash-commands fecha a expansao de
    skill/slash no prompt; --mode plan NAO entra: com slash desligado ele nao tem efeito nenhum (stderr do agy,
    medido 23/10/2026). --add-dir libera a leitura das raizes que a SOLUCAO cita: sem isso o pedido de permissao em
    headless e auto-negado e a resposta sai VAZIA (medido 23/10/2026)."""
    a = [executavel or _agy(), '-p', prompt_texto, '--model', modelo_id, '--output-format', 'json',
         '--print-timeout', '%ds' % int(timeout), '--disable-slash-commands']
    for d in add_dirs:
        a += ['--add-dir', d]
    if agente:
        a += ['--agent', agente]
    return a


_RE_CAMINHO = re.compile(r'(?<![\w])([A-Za-z]:[\\/][^\s"\'<>|)\]`,;]+)')
# grafias relativas a home que a SOLUCAO usa (~/.gemini/..., %USERPROFILE%\..., $env:USERPROFILE\...): sem elas o
# juiz pedia permissao para ler ~/.gemini/GEMINI.md e a resposta saia vazia (rodada INDEFINIDA, medido 23/10/2026)
_RE_CAMINHO_HOME = re.compile(r'(?<![\w])(?:~|%USERPROFILE%|\$env:USERPROFILE|\$HOME)([\\/][^\s"\'<>|)\]`,;]+)')
_RAIZ_PROIBIDA = ('.secrets', '.credenciais', '.ssh', 'oauth', '.gnupg')
_PASTAS_PESSOAIS = ('documents', 'desktop', 'downloads', 'pictures', 'videos', 'music', 'onedrive', '.claude', '.gemini')
# dados do app Antigravity (conversas, brain, perfil do navegador): nunca inteiros; so uma subpasta citada (ex.: scratch\x)
_NUNCA_RAIZ = tuple(os.path.join('.gemini', a) for a in ('antigravity', 'antigravity-ide', 'antigravity-backup',
                                                           'antigravity-browser-profile'))   # separador do SO (29/10/2026)


def _raiz_git(pasta, home):
    p = os.path.abspath(pasta)
    while True:
        if os.path.normcase(p) == home or os.path.dirname(p) == p:
            return None
        if os.path.exists(os.path.join(p, '.git')):
            return p
        p = os.path.dirname(p)


_APP_TRABALHO = ('scratch', 'playground')                      # so uma SUBpasta destas (scratch\x), nunca a pasta inteira
_APP_TRABALHO_RASO = ('knowledge', 'global_workflows', '.agent')


def _raiz_do_app_permitida(n, home):
    """Raiz dentro dos dados do app Antigravity: so o que e trabalho. Fora dos dados do app: True."""
    for app in _NUNCA_RAIZ:
        base = os.path.normcase(os.path.join(home, app))
        if n == base:
            return False
        if n.startswith(base + os.sep):
            partes = n[len(base) + 1:].split(os.sep)
            return (partes[0] in _APP_TRABALHO and len(partes) >= 2) or partes[0] in _APP_TRABALHO_RASO
    return True


def raizes_de_leitura(texto, home=None, maximo=30):
    """Pastas a liberar ao juiz agy (--add-dir): a raiz git de cada caminho absoluto citado no texto, ou a pasta do
    arquivo quando nao ha .git acima. Deduplicada (subpasta de raiz ja liberada sai) e ordenada. Recusa a home, raiz
    de disco, pasta acima da home, pastas pessoais inteiras (Documents, .claude, .gemini...), os dados do app
    Antigravity inteiros e caminhos com .secrets/.credenciais/.ssh/oauth (o juiz nao le segredo)."""
    home_real = os.path.abspath(home or os.path.expanduser('~'))
    home = os.path.normcase(home_real)
    raizes = {}
    for cam in _caminhos_citados(texto, home_real):
        partes = os.path.normcase(cam).split(os.sep)
        if any(p in partes for p in _RAIZ_PROIBIDA):
            continue
        pasta = cam if os.path.isdir(cam) else os.path.dirname(cam)
        if not os.path.isdir(pasta):
            continue   # caminho que ainda nao existe (ex.: destino de uma migracao) nao libera a pasta-mae inteira
        raiz = _raiz_git(pasta, home) or pasta
        n = os.path.normcase(raiz)
        if n == home or home.startswith(n.rstrip(os.sep) + os.sep) or os.path.dirname(raiz) == raiz:
            continue
        if os.path.normcase(os.path.dirname(raiz)) == home and os.path.basename(n) in _PASTAS_PESSOAIS:
            continue   # Documents, Desktop, .claude... inteiros nunca: so uma subpasta citada de verdade
        if not _raiz_do_app_permitida(n, home):
            continue   # conversas/brain do app nao sao da conta do juiz; so o trabalho (scratch\x, playground\x...)
        raizes.setdefault(n, raiz)
    ordenadas = sorted(raizes)
    sem_filhas = [k for k in ordenadas if not any(k != pai and k.startswith(pai.rstrip(os.sep) + os.sep) for pai in ordenadas)]
    return [raizes[k] for k in sem_filhas][:maximo]


LIMITE_COPIA = 2 * 1024 * 1024
# v15.1 (fecho de 23/10/2026, Fable): VALOR com cara de chave, nunca a palavra solta ('api_key' em prosa de veredicto nao
# conta). Uma copia so-leitura de ~/.claude.json (chave de API em texto puro) ficou 3 h na instancia, dentro do
# --add-dir do juiz do Google; o conteudo nao foi lido (medido no sqlite do CLI), mas a trava faltava.
_RE_SEGREDO = [
    ('elevenlabs', re.compile(r'\bsk_[0-9a-f]{32}\b')),
    ('openai/openrouter', re.compile(r'\bsk-[A-Za-z0-9_-]{20,}')),
    ('google', re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b')),
    ('github', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{36}\b')),
    ('aws', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('slack', re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,}')),
    ('chave privada', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('json chave=valor', re.compile(r'"[A-Za-z_]*(?:api_?key|secret|token|password)[A-Za-z_]*"\s*:\s*"[^"\s]{20,}"', re.I)),
]


def _segredos_no_texto(texto):
    """[(linha, padrao)] ordenado, uma entrada por linha - o VALOR nunca sai daqui."""
    por_linha = {}
    for nome, rx in _RE_SEGREDO:
        for m in rx.finditer(texto):
            por_linha.setdefault(texto.count('\n', 0, m.start()) + 1, nome)
    return sorted(por_linha.items())


def _texto_de(cam):
    """Texto do arquivo, ou None quando e binario (NUL nos primeiros 8 KB), maior que LIMITE_COPIA ou ilegivel."""
    try:
        if os.path.getsize(cam) > LIMITE_COPIA:
            return None
        with open(cam, 'rb') as f:
            dados = f.read()
    except OSError:
        return None
    if b'\x00' in dados[:8192]:
        return None
    return dados.decode('utf-8', 'replace')


def segredos_na_instancia(pasta):
    """Pre-voo do juiz agy: varre a pasta da instancia (menos .git) por valor com cara de segredo.
    Devolve [(arquivo, linha, padrao)] sem o valor; vazio = pode chamar o juiz."""
    achados = []
    for raiz, pastas, arqs in os.walk(pasta):
        pastas[:] = [p for p in pastas if p != '.git']
        for a in sorted(arqs):
            cam = os.path.join(raiz, a)
            texto = _texto_de(cam)
            if texto is None:
                continue
            achados += [(cam, linha, nome) for linha, nome in _segredos_no_texto(texto)]
    return achados


# POSIX (29/10/2026): raizes comuns, nunca '/' solto (senao rotas de site e URLs virariam caminho); so onde o separador e '/'
_RE_CAMINHO_POSIX = re.compile(r'(?<![\w:/.~])(/(?:tmp|home|mnt|var|opt|srv|usr|etc|root|Users|private)/[^\s"\'<>|)\]`,;]+)')


def _caminhos_citados(texto, home_real):
    citados = [m.group(1) for m in _RE_CAMINHO.finditer(texto or '')]
    if os.sep == '/':
        citados += [m.group(1) for m in _RE_CAMINHO_POSIX.finditer(texto or '')]
    citados += [home_real + m.group(1) for m in _RE_CAMINHO_HOME.finditer(texto or '')]
    return [os.path.abspath(c.rstrip('.:').replace('/', os.sep)) for c in citados]


def copias_de_leitura(texto, pasta, raizes, home=None):
    """Arquivo citado que NAO cabe em nenhuma raiz liberada (ex.: ~/.gemini/GEMINI.md, cuja pasta inteira e recusada)
    ganha uma copia so-leitura em <instancia>/historico/leitura/ — a rodada 3 de 23/10/2026 morreu num view_file
    auto-negado desse arquivo. Nunca copia segredo (.secrets/.credenciais/.ssh/oauth) nem arquivo > 2 MB.
    Devolve [(origem, copia)]."""
    home_real = os.path.abspath(home or os.path.expanduser('~'))
    liberadas = [os.path.normcase(r).rstrip(os.sep) + os.sep for r in raizes] + [os.path.normcase(os.path.abspath(pasta)).rstrip(os.sep) + os.sep]
    destino = os.path.join(pasta, 'historico', 'leitura')
    if os.path.isdir(destino):     # v15.1: a pasta e refeita a cada rodada; resto de rodada antiga (o .claude.json) nunca fica
        for velho in os.listdir(destino):
            if os.path.isfile(os.path.join(destino, velho)):
                os.remove(os.path.join(destino, velho))
    copias, vistos = [], set()
    for cam in _caminhos_citados(texto, home_real):
        n = os.path.normcase(cam)
        if n in vistos or not os.path.isfile(cam):
            continue
        vistos.add(n)
        if any(n.startswith(r) for r in liberadas):
            continue
        if any(p in n.split(os.sep) for p in _RAIZ_PROIBIDA) or os.path.getsize(cam) > LIMITE_COPIA:
            continue
        if os.path.normcase(os.path.dirname(cam)) == os.path.normcase(home_real):
            continue   # arquivo solto na home (~/.claude.json, credenciais de ferramentas): nunca vai ao juiz
        texto_cam = _texto_de(cam)
        if texto_cam is None or _segredos_no_texto(texto_cam):
            continue   # v15.1: binario, grande ou com VALOR de segredo dentro: nunca vai ao juiz, seja qual for o caminho
        os.makedirs(destino, exist_ok=True)
        nome = os.path.basename(cam)
        alvo = os.path.join(destino, nome)
        if os.path.exists(alvo) and not os.path.samefile(alvo, cam) if os.path.exists(alvo) else False:
            alvo = os.path.join(destino, hashlib.sha256(os.path.dirname(n).encode('utf-8')).hexdigest()[:8] + '-' + nome)
        shutil.copyfile(cam, alvo)
        copias.append((cam, alvo))
    return copias


_RE_RESET = re.compile(r'Resets in\s+(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', re.I)


def prazo_de_reset(texto, agora=None):
    """'Resets in 126h14m33s' -> datetime do retorno da cota; None quando o texto nao diz."""
    m = _RE_RESET.search(texto or '')
    if not m or not any(m.groups()):
        return None
    h, mi, s = (int(g or 0) for g in m.groups())
    return (agora or datetime.now()) + timedelta(hours=h, minutes=mi, seconds=s)


def _ler_cota(caminho):
    try:
        with open(caminho, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _gravar_cota(caminho, modelo_id, ate):
    d = _ler_cota(caminho)
    d[modelo_id] = ate.strftime('%Y-%m-%dT%H:%M:%S')
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, indent=1)


def esgotado_ate(caminho, modelo_id, agora=None):
    """datetime ate quando o modelo esta sem cota (cache local); None = pode tentar."""
    v = _ler_cota(caminho).get(modelo_id)
    if not v:
        return None
    try:
        ate = datetime.strptime(v, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return None
    return ate if ate > (agora or datetime.now()) else None


_RE_DADOS = re.compile(r'^Dados\b.*pessoais\s*$', re.M)


def backend_forcado(pasta):
    """D2 (23/10/2026): linha do ESTADO que COMECA com 'Dados' e termina em 'pessoais' = instancia com dado pessoal
    de cliente: o juiz e o Claude local, nunca o agy (Google). So a secao ESTADO conta; prosa no resto nao dispara."""
    sol = os.path.join(pasta, 'solucao.txt')
    if not os.path.exists(sol):
        return None
    texto = _ler(sol)
    inicio = texto.find('=== ESTADO')
    fim = min([i for i in (texto.find('=== TAREFA'), texto.find('=== RUBRICA'), texto.find('=== SOLUCAO')) if i > 0] or [len(texto)])
    return 'claude' if _RE_DADOS.search(texto[max(inicio, 0):fim]) else None


def tripwire_retrato(pasta, extra_ignorar=()):
    """(tamanho, mtime_ns) de cada arquivo da instancia que o juiz NAO pode tocar (fora historico/, custo.log,
    veredicto*.md e os demais de TRIPWIRE_IGNORA)."""
    ign = set(TRIPWIRE_IGNORA) | {os.path.normcase(os.path.abspath(e)) for e in extra_ignorar if e}
    r = {}
    for raiz, pastas, arqs in os.walk(pasta):
        pastas[:] = [p for p in pastas if p not in TRIPWIRE_IGNORA]
        for a in arqs:
            cam = os.path.join(raiz, a)
            if a in TRIPWIRE_IGNORA or (a.startswith('veredicto') and a.endswith('.md')) or os.path.normcase(os.path.abspath(cam)) in ign:
                continue
            try:
                st = os.stat(cam)
            except OSError:
                continue
            r[os.path.relpath(cam, pasta).replace('\\', '/')] = (st.st_size, st.st_mtime_ns)
    return r


def tripwire_violacoes(antes, depois):
    """Arquivos novos, alterados ou sumidos entre os dois retratos."""
    return sorted(set(k for k, v in depois.items() if antes.get(k) != v) | set(antes) - set(depois))


def _executar_agy(args, cwd, timeout):
    r = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def chamar_agy(pasta, modelo, p, arquivo_saida, timeout=TIMEOUT_PADRAO, tentativas=2, executar=None, cota_cache=None, agora=None):
    """Roda `agy -p` na instancia com a fila de cota; devolve (texto, resp, status) como chamar_juiz.
    status: ok | cota (fila toda esgotada) | permissao (resposta vazia) | timeout (2x) | erro | violacao (tripwire).
    O juiz NAO grava: o veredicto vem no campo `response` e e gravado aqui em arquivo_saida; fora do ok sai
    VEREDICTO: INDEFINIDO com o motivo (nunca AJUSTE, nunca cai calado no claude -p). resp['_ocombo'] leva modelo
    usado, fila e tripwire para o custo.log."""
    cota_cache = cota_cache or COTA_CACHE
    executar = executar or _executar_agy
    alvo = os.path.join(pasta, arquivo_saida)
    if os.path.exists(alvo):
        os.remove(alvo)
    hist = os.path.join(pasta, 'historico')
    os.makedirs(hist, exist_ok=True)
    prompt_arg = p
    if len(p) >= LIMITE_PROMPT:
        nome = 'prompt.r%d.txt' % max(rodada_atual(pasta), 1)
        _gravar(os.path.join(hist, nome), p)
        prompt_arg = ('Leia o arquivo historico/%s nesta pasta: ele e o seu prompt inteiro (nao coube na linha de '
                      'comando). Siga-o a risca.' % nome)
    sol = os.path.join(pasta, 'solucao.txt')
    texto_sol = _ler(sol) if os.path.exists(sol) else ''
    raizes = raizes_de_leitura(texto_sol)
    _gravar(os.path.join(hist, 'agy.add-dir.txt'), '\n'.join(raizes) + '\n')   # auditoria: o que o juiz pode ler
    print('[juiz] agy --add-dir (%d): %s' % (len(raizes), '; '.join(raizes)))
    copias = copias_de_leitura(texto_sol, pasta, raizes)
    _gravar(os.path.join(hist, 'agy.copias.txt'), ''.join('%s -> %s\n' % c for c in copias))
    if copias:
        print('[juiz] agy copias so-leitura em historico/leitura: %d' % len(copias))
        prompt_arg = ('ARQUIVOS CITADOS FORA DAS PASTAS LIBERADAS TEM COPIA SO-LEITURA NESTA INSTANCIA (leia a copia, nunca o '
                      'original): ' + '; '.join('%s = historico/leitura/%s' % (o, os.path.basename(c)) for o, c in copias) + '. ' + prompt_arg)
    agente = os.environ.get('OCOMBO_AGY_AGENTE', 'juiz') or None
    fila, registro = fila_agy(modelo[4:] if modelo.startswith('agy:') else modelo), []
    resp, status, motivo, usado = {}, 'cota', '', None
    segredos = segredos_na_instancia(pasta)   # v15.1: valor com cara de chave na instancia = o juiz do Google nao e chamado
    if segredos:
        status = 'segredo'
        motivo = ('SEGREDO na pasta da instancia: %s. O juiz nao foi chamado: tire o arquivo do alcance (ou troque a chave) '
                  'e rode de novo.' % '; '.join('%s:%d (%s)' % (os.path.relpath(a, pasta), l, n) for a, l, n in segredos[:8]))
        print('[juiz] agy NAO chamado: ' + motivo)
    antes = tripwire_retrato(pasta, (cota_cache,))
    for mid in (fila if status != 'segredo' else []):
        if esgotado_ate(cota_cache, mid, agora):
            registro.append('%s=esgotado' % mid)
            continue
        r = None
        for _ in range(tentativas):
            try:
                r = executar(argumentos_agy(mid, prompt_arg, timeout, raizes, agente), pasta, timeout + 60)
                break
            except subprocess.TimeoutExpired:
                r = None
        if r is None:
            registro.append('%s=timeout' % mid)
            status, motivo = 'timeout', 'O juiz agy (%s) estourou o tempo (%d s) %d vezes. Repita a rodada.' % (mid, timeout, tentativas)
            break
        rc, out, err = r
        _gravar(os.path.join(hist, 'agy.%s.%s.json' % (mid, arquivo_saida)), out or err or '')
        try:
            resp = json.loads(out)
        except ValueError:
            resp = {'status': 'ERROR', 'error': (out or err or '')[:500], 'response': ''}
        erro = '%s %s' % (resp.get('error') or '', err or '')
        if resp.get('status') == 'ERROR' and (rc == 3 or 'RESOURCE_EXHAUSTED' in erro or 'quota' in erro.lower()):
            _gravar_cota(cota_cache, mid, prazo_de_reset(erro, agora) or ((agora or datetime.now()) + timedelta(hours=1)))
            registro.append('%s=esgotado' % mid)
            continue
        if resp.get('status') == 'SUCCESS' and (resp.get('response') or '').strip():
            registro.append('%s=ok' % mid)
            status, usado = 'ok', mid
            break
        if resp.get('status') == 'SUCCESS':
            registro.append('%s=vazio' % mid)
            status = 'permissao'
            motivo = ('O juiz agy (%s) respondeu VAZIO: um pedido de permissao foi auto-negado em headless (libere a raiz '
                      'com --add-dir ou permissions.allow). stderr: %s' % (mid, (err or '').strip()[:400]))
            break
        registro.append('%s=erro' % mid)
        status, motivo = 'erro', 'O juiz agy (%s) falhou: %s' % (mid, erro.strip()[:400])
        break
    viol = tripwire_violacoes(antes, tripwire_retrato(pasta, (cota_cache,)))
    if viol:
        status = 'violacao'
        motivo = 'TRIPWIRE: o juiz alterou a pasta da instancia (%s). Travas violadas; nada e julgado.' % ', '.join(viol)
    if status == 'cota' and not motivo:
        motivo = ('Fila de cota esgotada (%s). Nao e AJUSTE: espere a cota voltar ou rode com OCOMBO_JUIZ_CLAUDE=1.'
                  % ', '.join(registro))
    if status == 'ok':
        _gravar(alvo, resp.get('response'))
    else:
        _gravar(alvo, 'VEREDICTO: INDEFINIDO\n\n%s\nfila: %s\n' % (motivo, ', '.join(registro)))
    resp = dict(resp)
    resp['_ocombo'] = {'modelo': usado or fila[0], 'fila': ','.join(registro), 'tripwire': len(viol), 'status': status}
    return _ler(alvo), resp, status


def resolver_modelo(explicito, p, pasta=None):
    """Precedencia v9: argumento da linha de comando > modo > padrao. v16: juiz agy vindo do modo ou do padrao vira
    MODELO_CLAUDE sempre (o Gemini saiu do processo, 26/10/2026); so o explicito ainda manda."""
    if explicito:
        return explicito
    modelo = p['juiz']
    if backend_de(modelo) == 'agy':
        return MODELO_CLAUDE
    return modelo


def resolver_timeout(explicito, p):
    return explicito if explicito is not None else p['timeout']


def resolver_effort(explicito, p):
    """v13: --effort explicito > juiz_effort do modo > None (a CLI decide). Valor fora da lista levanta."""
    import modos
    return modos.validar_effort(explicito) if explicito is not None else p['juiz_effort']


def escada_ativa(pasta):
    """v13: a escada liga por OCOMBO_ESCADA=1 OU por `escada: sim` na linha 'Modo deste ciclo' do
    solucao.txt (iniciar.py --escada) — o plano e a fonte, a conversa nao."""
    if os.environ.get('OCOMBO_ESCADA') == '1':
        return True
    sol = os.path.join(pasta, 'solucao.txt')
    if not os.path.exists(sol):
        return False
    for linha in _ler(sol).split('\n'):
        if linha.startswith('Modo deste ciclo:'):
            return 'escada: sim' in linha
    return False


def chamar_juiz(pasta, modelo, p, arquivo_saida, timeout=TIMEOUT_PADRAO, tentativas=2, effort=None, executar=None, cota_cache=None):
    """Roda `claude -p` na instancia com timeout; devolve (texto_saida, resp_json, status).
    status: 'ok' | 'timeout'. Se o modelo nao gravou arquivo_saida, grava o campo result.
    v15: id com prefixo agy: vai para chamar_agy (fila de cota, tripwire, veredicto pelo campo response)."""
    if backend_de(modelo) == 'agy':
        return chamar_agy(pasta, modelo, p, arquivo_saida, timeout, tentativas, executar=executar, cota_cache=cota_cache)
    alvo = os.path.join(pasta, arquivo_saida)
    if os.path.exists(alvo):
        os.remove(alvo)
    resp, status = {}, 'timeout'
    for _ in range(tentativas):
        try:
            # PROMPT POR STDIN, nunca por argumento: o claude.cmd (Windows) re-interpreta a linha de
            # comando, e um prompt com aspas/barras (a rubrica de rubrica.py) engoliu o `--output-format
            # json` — o bruto veio como texto e o custo saiu "sem usage" (05/09/2026, 2 rodadas).
            # encoding='utf-8' obrigatorio: o JSON vem em UTF-8 e o Windows decodificaria em cp1252.
            r = subprocess.run(argumentos_claude(modelo, effort), cwd=pasta,
                               input=p, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=timeout)
        except subprocess.TimeoutExpired:
            continue
        os.makedirs(os.path.join(pasta, 'historico'), exist_ok=True)
        _gravar(os.path.join(pasta, 'historico', 'claude.%s.json' % arquivo_saida), r.stdout or r.stderr or '')
        try:
            resp = json.loads(r.stdout)
        except ValueError:
            resp = {'result': r.stdout or r.stderr}
        status = 'ok'
        break
    if status == 'timeout':
        _gravar(alvo, 'VEREDICTO: INDEFINIDO\n\nO juiz %s estourou o tempo (%d s) %d vezes. Nao e AJUSTE: '
                      'repita a rodada ou troque o modelo.\n' % (modelo, timeout, tentativas))
    elif not os.path.exists(alvo):
        _gravar(alvo, str(resp.get('result') or ''))
    return _ler(alvo), resp, status


def comando_prova(pasta, nt=None):
    """Comando do portao da instancia ou None: prova.bat via cmd no Windows, prova.sh via sh no POSIX
    (v7, 07/09/2026: a skill ficou publica e o juiz precisa rodar fora do Windows)."""
    nt = (os.name == 'nt') if nt is None else nt
    bat, sh = os.path.join(pasta, 'prova.bat'), os.path.join(pasta, 'prova.sh')
    if nt and os.path.exists(bat):
        return ['cmd', '/c', bat]
    if not nt and os.path.exists(sh):
        return ['sh', sh]
    return None


def _prova(pasta):
    cmd = comando_prova(pasta)
    if cmd is None:
        return True, ''
    r = subprocess.run(cmd, cwd=pasta, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, errors='replace')
    return r.returncode == 0, (r.stdout or '') + (r.stderr or '')


def _ajuste_sem_juiz(pasta, n, titulo, corpo, rotulo):
    _gravar(os.path.join(pasta, 'veredicto.md'), 'VEREDICTO: AJUSTE\n\n%s\n%s\n' % (titulo, corpo))
    registrar_custo(pasta, {'rodada': n, 'modelo': '-', 'usd': None, 'input': None}, status=rotulo + ' - juiz nao chamado (0 tokens)')
    print('[%s] AJUSTE sem juiz (rodada %d)' % (rotulo, n))
    return 1


def _ledger(pasta, n, v, usd):
    """v5: cada veredicto vai ao ledger da regua (~/.claude/ocombo-ledger.jsonl) para o cupom do dia."""
    try:
        import ledger
        ledger.gravar({'instancia': os.path.basename(os.path.abspath(pasta)), 'tipo': 'veredicto',
                       'rodada': 'r%d' % n, 'veredicto': v, 'usd': usd})
    except Exception as e:  # ledger nunca derruba o juiz
        print('[juiz] aviso: ledger nao gravado (%s)' % e)


def _rodadas_ajuste(pasta):
    """Quantas rodadas ja terminaram em AJUSTE (le historico/veredicto.rN.md)."""
    h = os.path.join(pasta, 'historico')
    if not os.path.isdir(h):
        return 0
    return sum(1 for f in os.listdir(h) if f.startswith('veredicto.r') and veredicto(_ler(os.path.join(h, f))) == 'AJUSTE')


def julgar(pasta, modelo=None, timeout=None, effort=None):
    import modos
    import triagem
    perf = modos.perfil()                       # v9: OCOMBO_MODO manda quando a linha de comando cala
    pasta = os.path.abspath(pasta)
    escada = ''
    if escada_ativa(pasta):                     # v13: sobe 1 degrau por rodada AJUSTE; padrao desligado
        degrau = modos.escalar(perf['chave'], _rodadas_ajuste(pasta))
        if degrau != perf['chave']:
            escada = ' escada %s->%s' % (perf['chave'], degrau)
        perf = modos.perfil(degrau)
    if not os.path.exists(os.path.join(pasta, 'solucao.txt')):
        print('[erro] solucao.txt nao encontrado em', pasta)
        return 2
    pedido = modelo
    modelo = resolver_modelo(modelo, perf, pasta)
    if not pedido and backend_de(perf['juiz']) == 'agy' and backend_de(modelo) == 'claude':
        print('[juiz] aviso: juiz do modo e %s, mas esta rodada vai ao %s (%s)' % (
            perf['juiz'], modelo, 'OCOMBO_JUIZ_CLAUDE=1' if os.environ.get('OCOMBO_JUIZ_CLAUDE') == '1' else 'ESTADO declara dados pessoais (D2)'))
    timeout = resolver_timeout(timeout, perf)
    effort = resolver_effort(effort, perf) if backend_de(modelo) == 'claude' else None
    n = snapshot(pasta)
    ok, saida = _prova(pasta)
    if not ok:
        return _ajuste_sem_juiz(pasta, n, 'A PROVA EXECUTAVEL FALHOU (exit != 0). Corrija ate a prova passar. Saida:',
                                '```\n' + saida.strip()[-2000:] + '\n```', 'prova VERMELHA')
    probs = triagem.triagem(pasta)
    if probs:
        return _ajuste_sem_juiz(pasta, n, 'A TRIAGEM DETERMINISTICA reprovou a instancia (forma, 0 tokens):',
                                '\n'.join('- ' + p for p in probs), 'triagem')
    d = delta_da_rodada(pasta, n)
    triagem.manifesto(pasta)
    ant = os.path.join(pasta, 'historico', 'veredicto.r%d.md' % (n - 1))
    texto_ant = _ler(ant) if os.path.exists(ant) else None
    fails = pendentes_com_novos(texto_ant, _ler(os.path.join(pasta, 'solucao.txt')),   # 17/10: + critério novo
                                historico=historico_de_veredictos(pasta)[:max(n - 1, 0)])
    texto, resp, status = chamar_juiz(pasta, modelo, prompt(rodada_do_prompt(n, texto_ant), fails, bool(d), backend=backend_de(modelo)),
                                      'veredicto.md', timeout,
                                      effort=effort)
    shutil.copyfile(os.path.join(pasta, 'veredicto.md'), os.path.join(pasta, 'historico', 'veredicto.r%d.md' % n))
    c = custo(resp, n, modelo, effort)
    linha = registrar_custo(pasta, c, status=status)
    v = veredicto(texto)
    if v == 'APROVADO':
        gravar_carimbo(pasta)   # v6: carimbo preso ao sha256 do plano aprovado
    else:
        apagar_carimbo(pasta)
    _ledger(pasta, n, v, c.get('usd'))
    print('[juiz] rodada %d modelo %s%s (modo %s%s) -> %s | %s'
          % (n, c['modelo'], (' effort ' + effort) if effort else '', perf['apelido'], escada, v, linha))
    if status not in ('ok', 'timeout'):
        print('[juiz] aviso: rodada INDEFINIDA pelo backend agy (%s) - veja veredicto.md; nao e AJUSTE' % status)
    return {'APROVADO': 0, 'AJUSTE': 1}.get(v, 3)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # console cp1252 (armadilha do dia)
    except AttributeError:
        pass
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    if a[0] == '--carimbo':   # v6: confere o carimbo sem gastar token (exit 0 valido | 1 caducou | 2 nenhum)
        est, atual, grav = carimbo(a[1])
        print('[carimbo] %s | solucao.txt agora %s | aprovado %s' % (est or 'NENHUM', atual[:12], (grav or '-')[:12]))
        sys.exit({'APROVADO': 0, 'CADUCOU': 1}.get(est, 2))
    to = None                      # v9: None = deixa o modo decidir; --timeout explicito vence
    if '--timeout' in a:
        i = a.index('--timeout')
        to = int(a[i + 1])
        a = a[:i] + a[i + 2:]
    ef = None                      # v13: --effort explicito vence o do modo (lista fechada, validada antes)
    if '--effort' in a:
        i = a.index('--effort')
        ef = a[i + 1]
        a = a[:i] + a[i + 2:]
    sys.exit(julgar(a[0], a[1] if len(a) > 1 else None, to, ef))
