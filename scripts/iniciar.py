# -*- coding: utf-8 -*-
"""Um comando para abrir uma instancia do combo (idempotente).

Uso: python iniciar.py <pasta> [--tipo bot|site|script-agendado|receita-maquina|skill|texto|pesquisa|desenho|acao]
     [--modo 0..10|f1|3+|3+2|7-] [--escada]
     [--palavras p1 p2 ...]
Faz: loop_init.py (pontes do loop-agente) · solucao.txt a partir de assets/solucao.modelo.txt + rubrica do
tipo (assets/rubricas/<tipo>.txt) + contexto herdado vindo de decisoes.py <palavras> · evidencias/ e
corpus/ · prova.bat modelo. NAO sobrescreve solucao.txt nem prova.bat existentes.
v9: --modo grava a linha do modo no ESTADO (modos.py; sem --modo o ciclo e o modo 0, o padrao de sempre).
v12: os tipos texto|pesquisa|desenho|acao (pacotes por natureza) gravam a linha 'Pacote' depois de 'Papeis' e
reescrevem 'Lamina atual'; os 5 tipos de codigo saem byte a byte como antes (padrao continua skill).
v13: --modo aceita a dose colada ('3+' sobe um degrau, '7-' desce; modos.interpretar) e --escada grava
`escada: sim` na linha do modo: o juiz.py sobe 1 degrau por rodada AJUSTE lendo o plano, sem variavel.
"""
import os
import subprocess
import sys

import decisoes
import modos

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(AQUI)
LOOP_INIT = os.environ.get('OCOMBO_LOOP_INIT') or os.path.join(AQUI, 'loop_init.py')
TIPOS_CODIGO = ('bot', 'site', 'script-agendado', 'receita-maquina', 'skill')
TIPOS_PACOTE = ('texto', 'pesquisa', 'desenho', 'acao')   # v12: pacotes por natureza (references/pacotes/)
TIPOS = TIPOS_CODIGO + TIPOS_PACOTE
LAMINA_PACOTE = 'Lamina atual : [grelha | juiz | akita=portao antes da peca | producao so se a regua pedir]'


def _ler(cam):
    with open(cam, encoding='utf-8', errors='replace') as f:
        return f.read()


def aplicar_modo(texto, perfil, escada=False):
    """Troca a linha 'Modo deste ciclo:' do ESTADO pela do perfil escolhido (v9). Sem a linha no modelo,
    devolve o texto intacto — instancia antiga continua valendo. v13: escada=True anexa `escada: sim`."""
    saida = []
    for linha in texto.split('\n'):
        saida.append(modos.linha_estado(perfil, escada) if linha.startswith('Modo deste ciclo:') else linha)
    return '\n'.join(saida)


def aplicar_pacote(texto, tipo):
    """v12: nos tipos de pacote poe 'Pacote       : <tipo> (ler references/pacotes/<tipo>.md)' logo depois da
    linha 'Papeis' e reescreve 'Lamina atual' sem vocabulario de codigo. Nos tipos de codigo (e em tipo
    desconhecido) devolve o texto intacto: o caminho de codigo nao muda nem um byte."""
    if tipo not in TIPOS_PACOTE:
        return texto
    saida = []
    for linha in texto.split('\n'):
        if linha.startswith('Lamina atual :'):
            saida.append(LAMINA_PACOTE)
            continue
        saida.append(linha)
        if linha.startswith('Papeis       :'):
            saida.append('Pacote       : %s (ler references/pacotes/%s.md)' % (tipo, tipo))
    return '\n'.join(saida)


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


def iniciar(pasta, tipo='skill', palavras=(), rodar_loop_init=True, memoria_dir=None, modo=0, escada=False):
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
            f.write(aplicar_pacote(aplicar_modo(montar_solucao(modelo, rub, herdado),
                                                modos.perfil(modos.interpretar(modo)), escada), tipo))
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
    pasta, tipo, palavras, modo = a[0], 'skill', [], 0
    if '--tipo' in a:
        tipo = a[a.index('--tipo') + 1]
    if '--modo' in a:
        modo = a[a.index('--modo') + 1]
    if '--palavras' in a:
        palavras = a[a.index('--palavras') + 1:]
    if tipo not in TIPOS:
        print('tipo invalido; use um de', TIPOS)
        sys.exit(2)
    escada = '--escada' in a
    try:
        modo = modos.interpretar(modo)          # v13: '3+' -> 4; fora da escala levanta antes de criar a pasta
        perf = modos.perfil(modo)
    except ValueError as e:
        print('[iniciar]', e)
        sys.exit(2)
    p, mud = iniciar(pasta, tipo, palavras, modo=modo, escada=escada)
    print('[iniciar] instancia pronta em %s | mudancas=%d' % (p, mud))
    print('[iniciar] ' + modos.resumo(perf) + (' | escada: sim' if escada else ''))
