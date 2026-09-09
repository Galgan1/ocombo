# -*- coding: utf-8 -*-
"""Juiz cross-model POR DIFF com custo medido (ocombo v2, 05/09/2026; v3 = triagem, manifesto, timeout,
historico global).

Uso:  python juiz.py <pasta_da_instancia> [modelo] [--timeout SEG]      (padrao: claude-sonnet-5, 900 s)

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
from datetime import datetime

MODELO_PADRAO = 'claude-sonnet-5'
TIMEOUT_PADRAO = 900
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


def custo(resp, rodada, modelo):
    """Extrai usage/custo do JSON do `claude -p --output-format json`. Ausente -> None."""
    u = resp.get('usage') or {}
    usd = resp.get('total_cost_usd')
    ms = resp.get('duration_ms')
    return {
        'rodada': rodada, 'modelo': modelo,
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
    if c['usd'] is None and c['input'] is None:
        return '%s %s %s sem usage' % (carimbo, rod, c['modelo'])
    return ('%s %s %s in=%s out=%s cache_read=%s cache_write=%s usd=%s s=%s turnos=%s'
            % (carimbo, rod, c['modelo'], c['input'], c['output'], c['cache_read'],
               c['cache_write'], c['usd'], c['segundos'], c['turnos']))


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
    if re.search(r'\bAPROVADO\b', t):
        return 'APROVADO'
    if 'AJUSTE' in t:
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


def prompt(rodada, fails, tem_delta, caveman=None):
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
            'SOLUCAO/ENTREGA citam ou que um criterio exige. '
            'Escreva veredicto.md nesta pasta, sobrescrevendo. Nao peca confirmacao. ') + bloco_caveman(caveman)
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


def chamar_juiz(pasta, modelo, p, arquivo_saida, timeout=TIMEOUT_PADRAO, tentativas=2):
    """Roda `claude -p` na instancia com timeout; devolve (texto_saida, resp_json, status).
    status: 'ok' | 'timeout'. Se o modelo nao gravou arquivo_saida, grava o campo result."""
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
            r = subprocess.run([_claude(), '-p', '--model', modelo, '--permission-mode', 'acceptEdits',
                                '--output-format', 'json', '--no-session-persistence'], cwd=pasta,
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


def julgar(pasta, modelo=MODELO_PADRAO, timeout=TIMEOUT_PADRAO):
    import triagem
    pasta = os.path.abspath(pasta)
    if not os.path.exists(os.path.join(pasta, 'solucao.txt')):
        print('[erro] solucao.txt nao encontrado em', pasta)
        return 2
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
    fails = pendentes_de(_ler(ant)) if os.path.exists(ant) else []
    texto, resp, status = chamar_juiz(pasta, modelo, prompt(n, fails, bool(d)), 'veredicto.md', timeout)
    shutil.copyfile(os.path.join(pasta, 'veredicto.md'), os.path.join(pasta, 'historico', 'veredicto.r%d.md' % n))
    c = custo(resp, n, modelo)
    linha = registrar_custo(pasta, c, status=status)
    v = veredicto(texto)
    if v == 'APROVADO':
        gravar_carimbo(pasta)   # v6: carimbo preso ao sha256 do plano aprovado
    else:
        apagar_carimbo(pasta)
    _ledger(pasta, n, v, c.get('usd'))
    print('[juiz] rodada %d modelo %s -> %s | %s' % (n, modelo, v, linha))
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
    to = TIMEOUT_PADRAO
    if '--timeout' in a:
        i = a.index('--timeout')
        to = int(a[i + 1])
        a = a[:i] + a[i + 2:]
    sys.exit(julgar(a[0], a[1] if len(a) > 1 else MODELO_PADRAO, to))
