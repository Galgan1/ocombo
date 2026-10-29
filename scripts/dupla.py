# -*- coding: utf-8 -*-
"""Dupla de juizes: um segundo modelo julga o MESMO estado (sem novo snapshot) e a concordancia por
criterio vira concordancia.md. Discordancia alta = rubrica mal escrita, nao "juiz ruim".

Uso: python dupla.py <pasta_da_instancia> <modeloB> [--effort e] [--timeout s]   (o veredicto.md atual e o do juiz A)
     (17/10/2026: sem --effort/--timeout o B segue o modo, OCOMBO_MODO, como o juiz.py; antes rodava sem effort e com 900 s)
     python dupla.py --balanco                          (v6: ultimos 10 ciclos com dupla, exit 1 = alerta)
Grava veredicto.<modeloB>.md e concordancia.md; custo no custo.log com rotulo "dupla"; evento "dupla" no ledger
com quantas vezes B aprovou o que A reprovou (a favor do executor). Acima de 3 em 10 = decisao do dono: trocar o juiz.
"""
import os
import re
import shutil
import sys

import juiz

RE_ID = re.compile(r'\b(C\d+(?:\.\d+)?[a-c]?)\b')
RE_ROTULO = re.compile(r'\b(PASS|FAIL)\b')
JANELA = juiz.JANELA_ROTULO


def por_criterio(texto):
    """{'C1': 'PASS', 'C6.3': 'FAIL', 'C1a': 'PASS', ...}.
    Por linha: o rotulo (PASS/FAIL) vale para o PRIMEIRO criterio citado na linha (o sujeito), mesmo que
    venha no meio da frase ("Achado 4 — C7 ...: PASS") — os veredictos reais nao comecam a linha pelo
    criterio (05/09/2026, concordancia 0% por parser rigido). Primeiro rotulo por criterio vale.
    Tambem aceita "## C1" numa linha e "PASS." na seguinte."""
    saida = juiz.rotulos_canonicos(texto)
    if saida:
        return saida  # linhas `CRITERIO <id>: PASS|FAIL|N/A` — sem heuristica
    linhas = (texto or '').splitlines()
    for i, linha in enumerate(linhas):
        r = juiz.rotulo_do_criterio(linha)  # rotulo ate 60 chars DEPOIS do criterio, fora de aspas
        if not r and re.match(r'^\s*#+\s*', linha) and i + 1 < len(linhas):
            ids = RE_ID.findall(juiz.sem_citacoes(linha))
            rot = RE_ROTULO.search(juiz.sem_citacoes(linhas[i + 1])[:JANELA])
            if ids and rot:
                r = (ids[0], rot.group(1))
        if r:
            saida.setdefault(r[0], r[1])
    return saida


def comparar(veredicto_a, veredicto_b):
    a, b = por_criterio(veredicto_a), por_criterio(veredicto_b)
    def _ordem(k):
        m = re.match(r'C(\d+)(?:\.(\d+))?([a-c]?)', k)
        return (int(m.group(1)), int(m.group(2) or 0), m.group(3))
    chaves = sorted(set(a) | set(b), key=_ordem)
    por = {k: (a.get(k, '?'), b.get(k, '?')) for k in chaves}
    iguais = sum(1 for k in chaves if por[k][0] == por[k][1] and por[k][0] != '?')
    return {'por_criterio': por, 'taxa': (iguais / len(chaves)) if chaves else 0.0,
            'final': (juiz.veredicto(veredicto_a), juiz.veredicto(veredicto_b))}


def concordancia_md(c, nome_a, nome_b):
    linhas = ['# Concordancia entre juizes', '', '| criterio | %s | %s | igual |' % (nome_a, nome_b),
              '|---|---|---|---|']
    for k, (va, vb) in c['por_criterio'].items():
        linhas.append('| %s | %s | %s | %s |' % (k, va, vb, 'sim' if va == vb and va != '?' else 'NAO'))
    linhas += ['', 'Taxa de concordancia: %d%%' % round(c['taxa'] * 100),
               'Veredicto final: %s = %s | %s = %s' % (nome_a, c['final'][0], nome_b, c['final'][1]),
               '', 'Leitura: criterio com NAO e candidato a reescrita (ambiguo ou nao verificavel).']
    return '\n'.join(linhas) + '\n'


def discordancias(c):
    """v6: por criterio, B PASS onde A FAIL = B discordou A FAVOR do executor (juiz A mais duro); o inverso = contra."""
    por = c['por_criterio']
    return {'pro_executor': [k for k, (va, vb) in por.items() if va == 'FAIL' and vb == 'PASS'],
            'contra_executor': [k for k, (va, vb) in por.items() if va == 'PASS' and vb == 'FAIL']}


def balanco(itens, janela=10, limite=3):
    """v6 (arXiv 2607.21656: juiz mais fraco que o executor pode PIORAR o resultado): nos ultimos `janela`
    eventos tipo 'dupla' do ledger, soma quantas vezes o juiz B (Opus) aprovou o que o A (Sonnet) reprovou.
    alerta = acima de `limite` -> decisao de trocar o juiz padrao (regua: decisao do dono)."""
    ev = [e for e in itens if e.get('tipo') == 'dupla'][-janela:]
    pro = sum(int(e.get('pro_executor') or 0) for e in ev)
    contra = sum(int(e.get('contra_executor') or 0) for e in ev)
    return {'ciclos': len(ev), 'pro_executor': pro, 'contra_executor': contra, 'alerta': pro > limite,
            'instancias': [os.path.basename(str(e.get('instancia', '?')).rstrip('\\/')) for e in ev]}


def _ledger_dupla(pasta, n, disc, taxa):
    try:
        import ledger
        ledger.gravar({'instancia': os.path.basename(pasta), 'tipo': 'dupla', 'rodada': 'r%d' % n,
                       'taxa': round(taxa, 2), 'pro_executor': len(disc['pro_executor']),
                       'contra_executor': len(disc['contra_executor']),
                       'criterios_pro': disc['pro_executor'], 'criterios_contra': disc['contra_executor']})
    except Exception as e:  # ledger nunca derruba a dupla
        print('[dupla] aviso: ledger nao gravado (%s)' % e)


def rodar(pasta, modelo_b, effort=None, timeout=None):
    import modos
    perf = modos.perfil()   # 17/10/2026: o juiz B segue o modo como o A (opala = xhigh, 1800 s); explicito vence
    effort = juiz.resolver_effort(effort, perf)
    timeout = juiz.resolver_timeout(timeout, perf)
    pasta = os.path.abspath(pasta)
    ver_a = os.path.join(pasta, 'veredicto.md')
    if not os.path.exists(ver_a):
        print('[dupla] veredicto.md (juiz A) nao existe; rode juiz.py antes')
        return 2
    n = juiz.rodada_atual(pasta)
    d = juiz._ler(os.path.join(pasta, 'delta.patch')) if os.path.exists(os.path.join(pasta, 'delta.patch')) else ''
    hist = os.path.join(pasta, 'historico')
    ant_a = os.path.join(hist, 'veredicto.r%d.md' % (n - 1))
    ant_b = os.path.join(hist, 'veredicto.%s.r%d.md' % (modelo_b, n - 1))
    texto_a = juiz._ler(ant_a) if os.path.exists(ant_a) else None
    texto_b = juiz._ler(ant_b) if os.path.exists(ant_b) else None
    # 17/10/2026 (opala): o B julga o que o A deixou pendente (FAIL + N/A) E o que ELE reprovou ou pulou na rodada
    # anterior; antes so os FAIL do A entravam, e um B que reprovou sozinho nunca mais julgava o proprio FAIL
    pend = []
    sol = juiz._ler(os.path.join(pasta, 'solucao.txt'))
    hist_v = juiz.historico_de_veredictos(pasta)[:max(n - 1, 0)]
    for t in (texto_a, texto_b):            # 17/10: + critério da rubrica que nenhum veredicto julgou (emenda)
        for k in (juiz.pendentes_com_novos(t, sol, historico=hist_v + [t]) if t else []):
            if k not in pend:
                pend.append(k)
    # 17/10/2026 (opala r2, juiz B C9): o log da dupla prova o modo, o effort e o timeout que o B recebeu
    print('[dupla] rodada %d modelo %s%s timeout %s (modo %s)'
          % (n, modelo_b, (' effort ' + effort) if effort else '', timeout, perf['apelido']), flush=True)
    p = juiz.prompt(juiz.rodada_do_prompt(n, texto_b or texto_a), pend, bool(d))
    p = p.replace('veredicto.md', 'veredicto.%s.md' % modelo_b)
    if texto_b:
        p = p.replace('historico/veredicto.r%d.md' % (n - 1), 'historico/veredicto.%s.r%d.md' % (modelo_b, n - 1))
    saida, resp, status = juiz.chamar_juiz(pasta, modelo_b, p, 'veredicto.%s.md' % modelo_b, timeout, effort=effort)
    vb = os.path.join(pasta, 'veredicto.%s.md' % modelo_b)
    if os.path.exists(vb):
        os.makedirs(hist, exist_ok=True)
        shutil.copyfile(vb, os.path.join(hist, 'veredicto.%s.r%d.md' % (modelo_b, n)))
    juiz.registrar_custo(pasta, juiz.custo(resp, n, modelo_b, effort), rotulo='dupla', status=status)
    c = comparar(juiz._ler(ver_a), saida)
    md = concordancia_md(c, 'juizA', modelo_b)
    disc = discordancias(c)
    md += ('\nB a favor do executor (A FAIL, B PASS): %s\nB contra o executor (A PASS, B FAIL): %s\n'
           % (', '.join(disc['pro_executor']) or '-', ', '.join(disc['contra_executor']) or '-'))
    juiz._gravar(os.path.join(pasta, 'concordancia.md'), md)
    _ledger_dupla(pasta, n, disc, c['taxa'])
    print('[dupla] rodada %d: concordancia %d%% | A=%s B=%s | pro-executor=%d' % (n, round(c['taxa'] * 100), *c['final'], len(disc['pro_executor'])))
    return 0


def imprimir_balanco():
    import ledger
    b = balanco(ledger.carregar())
    print('[dupla] balanco dos ultimos %d ciclos com dupla: B a favor do executor %d x | contra %d x'
          % (b['ciclos'], b['pro_executor'], b['contra_executor']))
    print('  instancias: ' + (', '.join(b['instancias']) or '-'))
    print('  ALERTA: acima de 3 em 10 -> levar ao dono a troca do juiz padrao (regua: decisao)' if b['alerta']
          else '  ok: juiz padrao Sonnet segue (troca so acima de 3 em 10)')
    return 1 if b['alerta'] else 0


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] in ('-h', '--help'):   # v15: --help sai 0 como o modos.py (portao de regressao)
        print(__doc__)
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == '--balanco':
        sys.exit(imprimir_balanco())
    a = sys.argv[1:]
    ef = to = None
    if '--effort' in a:
        i = a.index('--effort')
        ef = a[i + 1] if i + 1 < len(a) else ''
        del a[i:i + 2]
    if '--timeout' in a:
        i = a.index('--timeout')
        to = int(a[i + 1]) if i + 1 < len(a) else None
        del a[i:i + 2]
    if len(a) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(rodar(a[0], a[1], ef, to))
