# -*- coding: utf-8 -*-
"""Fecho do combo pelo Fable 5.1 no maximo (ordem do dono, 03/10/2026): "no final das rodadas de ocombo o
fable 5.1 deve julgar sempre o resultado. se for aceitavel ele responde em .441 se nao ele manda rodar
novamente ate tres vezes."

Uso:  python fecho_fable.py <instancia>
Roda DEPOIS do carimbo final (`juiz.py --carimbo <instancia>` exit 0). Nao substitui o juiz cross-model das
rodadas: e o ultimo olhar, sobre o RESULTADO inteiro.
  exit 0  ACEITO     - a mensagem .441 ao dono esta em fecho.md (e na tela); o maestro a envia como esta
  exit 1  REFAZER    - motivos em fecho.md; o combo roda novas rodadas so sobre eles e chama o fecho de novo
  exit 2  uso errado, ou sem carimbo valido
  exit 3  teto: 3 julgamentos do Fable ja feitos - parada honesta, a pendencia vai ao dono
  exit 4  INDEFINIDO - resposta sem FECHO valido ou mensagem fora da forma .441 (nao conta como REFAZER)
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import juiz  # noqa: E402
import ledger  # noqa: E402

MODELO = 'claude-fable-5-1'
EFFORT = 'max'
TETO = 3
PALAVRAS, TOLERANCIA = 40, 4          # .441: quatro paragrafos de 40 palavras, +-10%
CUSTO = re.compile(r'\b(usd|us\$|d[oó]lar|tokens?|custo|custou|gast[oa]u?)\b|\$\s*\d', re.I)
TIMEOUT = 1800


def proxima(pasta):
    """Numero do proximo julgamento do Fable nesta instancia (historico/fecho.rN.md ja gravados + 1)."""
    hist = os.path.join(pasta, 'historico')
    if not os.path.isdir(hist):
        return 1
    feitos = [n for n in os.listdir(hist) if re.match(r'fecho\.r\d+\.md$', n)]
    return len(feitos) + 1


def estourou(pasta):
    return proxima(pasta) > TETO


def ler_fecho(texto):
    """Extrai decisao, paragrafos da MENSAGEM e MOTIVOS numerados da resposta do Fable."""
    m = re.search(r'^\s*FECHO:\s*(ACEITO|REFAZER)\b', texto or '', re.M | re.I)
    decisao = m.group(1).upper() if m else 'INDEFINIDO'
    paragrafos, motivos = [], []
    msg = re.search(r'^\s*MENSAGEM:\s*\n(.*?)(?=^\s*MOTIVOS:|\Z)', texto or '', re.M | re.S)
    if msg:
        paragrafos = [' '.join(p.split()) for p in re.split(r'\n\s*\n', msg.group(1).strip()) if p.strip()]
    mot = re.search(r'^\s*MOTIVOS:\s*\n(.*)', texto or '', re.M | re.S)
    if mot:
        motivos = [re.sub(r'^\s*\d+[.)]\s*', '', l).strip() for l in mot.group(1).split('\n')
                   if re.match(r'^\s*\d+[.)]\s*\S', l)]
    return {'decisao': decisao, 'paragrafos': paragrafos, 'motivos': motivos}


def problemas_441(paragrafos):
    """Forma da mensagem ao dono: 4 paragrafos, 36 a 44 palavras cada, sem custo (decisao de 29/09/2026)."""
    erros = []
    if len(paragrafos) != 4:
        erros.append('a mensagem tem %d paragrafos, nao 4' % len(paragrafos))
    for i, p in enumerate(paragrafos, 1):
        n = len(p.split())
        if abs(n - PALAVRAS) > TOLERANCIA:
            erros.append('paragrafo %d tem %d palavras (36 a 44)' % (i, n))
        if CUSTO.search(p):
            erros.append('paragrafo %d cita custo (proibido ao dono)' % i)
    return erros


def decidir(v):
    if v['decisao'] == 'ACEITO':
        return 'ACEITO' if not problemas_441(v['paragrafos']) else 'INDEFINIDO'
    if v['decisao'] == 'REFAZER':
        return 'REFAZER' if v['motivos'] else 'INDEFINIDO'
    return 'INDEFINIDO'


def prompt(n):
    return (
        'Voce e o JULGADOR FINAL do /ocombo (Fable 5.1, esforco maximo), julgamento %d de %d. As rodadas ja '
        'acabaram e o juiz cross-model carimbou. Julgue o RESULTADO inteiro, nao so o papel: abra solucao.txt '
        '(ESTADO, TAREFA, RUBRICA, SOLUCAO, ENTREGA), veredicto.md e as evidencias que a ENTREGA cita; rode '
        'comandos de prova se precisar. A pergunta e uma so: o dono pode receber isto como pronto?\n\n'
        'Responda EXATAMENTE em um dos dois formatos, nada antes de FECHO:\n\n'
        'FECHO: ACEITO\n\nMENSAGEM:\n<quatro paragrafos de 40 palavras cada (36 a 44), separados por linha em '
        'branco, registro cerebro frito (zero jargao, frases curtas, primeira pessoa "eu"): 1) o que eu '
        'verifiquei; 2) o que outro agente reportou; 3) o que nao deu para provar; 4) o que espera o sim do '
        'dono. Nunca cite custo, USD, tokens ou gasto.>\n\n'
        'ou\n\nFECHO: REFAZER\n\nMOTIVOS:\n1. <o que esta errado, com arquivo:linha, e o que mudar>\n2. ...\n\n'
        'REFAZER manda o combo rodar de novo so sobre os motivos (o teto e 3 julgamentos seus). Nao conserte '
        'nada: quem julga nao edita.\n' % (n, TETO))


def argumentos(executavel=None):
    a = juiz.argumentos_claude(MODELO, EFFORT, executavel)
    return a


def main(argv):
    if len(argv) != 2 or argv[1].startswith('-'):
        print(__doc__)
        return 2
    pasta = os.path.abspath(argv[1])
    estado = juiz.carimbo(pasta)[0]
    if estado != 'APROVADO':
        print('[fecho] sem carimbo valido (%s): rode `juiz.py --carimbo` ate exit 0 antes do Fable.' % estado)
        return 2
    if estourou(pasta):
        print('[fecho] TETO: %d julgamentos do Fable ja feitos. Parada honesta: leve a pendencia ao dono.' % TETO)
        return 3
    n = proxima(pasta)
    os.makedirs(os.path.join(pasta, 'historico'), exist_ok=True)
    try:
        r = subprocess.run(argumentos(), cwd=pasta, input=prompt(n), capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=TIMEOUT)
        bruto = r.stdout or r.stderr or ''
    except subprocess.TimeoutExpired:
        bruto = ''
    try:
        import json
        resp = json.loads(bruto)
    except ValueError:
        resp = {'result': bruto}
    texto = str(resp.get('result') or '')
    decisao = decidir(ler_fecho(texto))
    juiz.registrar_custo(pasta, juiz.custo(resp, 'fecho%d' % n, MODELO, EFFORT), rotulo='fecho')
    if decisao == 'INDEFINIDO':
        juiz._gravar(os.path.join(pasta, 'historico', 'fecho.indefinido.r%d.md' % n), texto)
        print('[fecho] INDEFINIDO (resposta sem FECHO valido ou fora da forma .441); nao conta no teto. '
              'Rode de novo.')
        return 4
    juiz._gravar(os.path.join(pasta, 'historico', 'fecho.r%d.md' % n), texto)
    juiz._gravar(os.path.join(pasta, 'fecho.md'), texto)
    ledger.gravar({'instancia': pasta, 'tipo': 'veredicto', 'texto': 'fecho Fable r%d: %s' % (n, decisao)})
    print(texto)
    return 0 if decisao == 'ACEITO' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
