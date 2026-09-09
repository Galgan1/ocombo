# -*- coding: utf-8 -*-
"""Um comando para abrir uma instancia do combo (idempotente).

Uso: python iniciar.py <pasta> [--tipo bot|site|script-agendado|receita-maquina|skill] [--palavras p1 p2 ...]
Faz: loop_init.py (pontes do loop-agente) · solucao.txt a partir de assets/solucao.modelo.txt + rubrica do
tipo (assets/rubricas/<tipo>.txt) + contexto herdado vindo de decisoes.py <palavras> · evidencias/ e
corpus/ · prova.bat modelo. NAO sobrescreve solucao.txt nem prova.bat existentes.
"""
import os
import subprocess
import sys

import decisoes

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(AQUI)
LOOP_INIT = os.environ.get('OCOMBO_LOOP_INIT') or os.path.join(AQUI, 'loop_init.py')
TIPOS = ('bot', 'site', 'script-agendado', 'receita-maquina', 'skill')


def _ler(cam):
    with open(cam, encoding='utf-8', errors='replace') as f:
        return f.read()


def montar_solucao(modelo, rubrica_tipo, herdado):
    """Troca o corpo da RUBRICA pelo do tipo e insere as decisoes herdadas depois da linha 'Contexto herdado'."""
    ini = modelo.index('=== RUBRICA')
    fim_cab = modelo.index('\n', ini) + 1
    prox = modelo.find('\n=== ', fim_cab)
    prox = len(modelo) if prox < 0 else prox + 1
    s = modelo[:fim_cab] + rubrica_tipo.rstrip('\n') + '\n\n' + modelo[prox:]
    if herdado:
        marca = 'Contexto herdado inviolavel'
        i = s.find(marca)
        if i >= 0:
            fim = s.index('\n', i) + 1
            s = s[:fim] + '\n'.join('  ' + h for h in herdado) + '\n' + s[fim:]
    return s


def iniciar(pasta, tipo='skill', palavras=(), rodar_loop_init=True, memoria_dir=None):
    """Devolve (pasta, mudancas): mudancas = quantas pecas foram criadas; 2a execucao = 0 (idempotente)."""
    pasta = os.path.abspath(pasta)
    mud = 0
    if not os.path.isdir(pasta):
        os.makedirs(pasta)
        mud += 1
    if rodar_loop_init and os.path.exists(LOOP_INIT) and not os.path.exists(os.path.join(pasta, 'verificar.bat')):
        subprocess.run([sys.executable, LOOP_INIT], cwd=pasta, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True)
        mud += 1
    for d in ('evidencias', 'corpus'):
        if not os.path.isdir(os.path.join(pasta, d)):
            os.makedirs(os.path.join(pasta, d))
            mud += 1
    sol = os.path.join(pasta, 'solucao.txt')
    ja = os.path.exists(sol) and 'TAREFA: (descreva' not in _ler(sol)
    if not ja:
        mud += 1
        modelo = _ler(os.path.join(SKILL, 'assets', 'solucao.modelo.txt'))
        rub_arq = os.path.join(SKILL, 'assets', 'rubricas', tipo + '.txt')
        rub = _ler(rub_arq) if os.path.exists(rub_arq) else 'C1. ...\nC9. REGRESSAO: o que ja passava continua passando (portao exit 0).\n'
        herdado = decisoes.buscar(decisoes.carregar(memoria_dir), list(palavras)) if palavras else []
        with open(sol, 'w', encoding='utf-8', newline='\n') as f:
            f.write(montar_solucao(modelo, rub, herdado))
    bat = os.path.join(pasta, 'prova.bat')
    if not os.path.exists(bat):
        mud += 1
        with open(bat, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write('@echo off\r\nREM portao duro da instancia: troque pelo comando real (exit 0 = verde)\r\n'
                    'cd /d "%~dp0"\r\necho troque este prova.bat pelo portao real & exit /b 1\r\n')
    return pasta, mud


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    if a[0].startswith('-'):   # 08/09/2026: `iniciar.py --help` criou uma instancia chamada "--help" dentro da skill
        print(__doc__)
        print('[iniciar] o 1o argumento e a PASTA da instancia; "%s" parece uma opcao. Nada criado.' % a[0])
        sys.exit(2)
    pasta, tipo, palavras = a[0], 'skill', []
    if '--tipo' in a:
        tipo = a[a.index('--tipo') + 1]
    if '--palavras' in a:
        palavras = a[a.index('--palavras') + 1:]
    if tipo not in TIPOS:
        print('tipo invalido; use um de', TIPOS)
        sys.exit(2)
    p, mud = iniciar(pasta, tipo, palavras)
    print('[iniciar] instancia pronta em %s | mudancas=%d' % (p, mud))
