# -*- coding: utf-8 -*-
"""Critica da RUBRICA por um modelo barato, ANTES da rodada 1 (fecha o ponto cego: quem escreve a
regua e quem sera julgado por ela).

Uso: python rubrica.py <pasta_da_instancia> [modelo]   (padrao: claude-haiku-4-5-20251001)
Le SO a secao RUBRICA de solucao.txt, chama `claude -p --output-format json` e grava
rubrica.critica.md; anexa a linha "rubrica" no custo.log (e no historico global). O executor decide o que
acatar e declara na SOLUCAO o que nao acatou e por que.
"""
import os
import re
import sys

import juiz

MODELO_PADRAO = 'claude-haiku-4-5-20251001'


def extrair_rubrica(texto):
    m = re.search(r'^=== RUBRICA\b[^\n]*\n(.*?)(?=^=== |\Z)', texto, re.M | re.S)
    return m.group(1).strip() if m else ''


def prompt_critica(rubrica):
    return ('Voce e o CRITICO DE RUBRICA de um loop executor->juiz. Nao julgue solucao nenhuma; '
            'critique apenas a RUBRICA abaixo. Para cada criterio diga: (a) e BINARIO (PASS/FAIL sem '
            'meio-termo)? (b) e VERIFICAVEL por comando, arquivo ou exit code citado no proprio criterio? '
            '(c) esta dentro do ESCOPO da tarefa ou e feature nova? Depois aponte o que FALTA: criterio de '
            'REGRESSAO (o que ja passava continua passando), criterio de honestidade da ENTREGA (fatos por '
            'comando, nao narrativa), e qualquer critério que o executor poderia satisfazer trapaceando '
            '(ex.: alegar sem anexar). Termine com uma lista "REESCREVER:" com os criterios reescritos de '
            'forma binaria e verificavel. Nao escreva VEREDICTO. Responda em pt-BR, no maximo 60 linhas.\n\n'
            '=== RUBRICA ===\n' + rubrica + '\n')


def criticar(pasta, modelo=MODELO_PADRAO):
    pasta = os.path.abspath(pasta)
    texto = juiz._ler(os.path.join(pasta, 'solucao.txt'))
    rub = extrair_rubrica(texto)
    if not rub:
        print('[rubrica] solucao.txt sem secao RUBRICA')
        return 2
    saida, resp, status = juiz.chamar_juiz(pasta, modelo, prompt_critica(rub), 'rubrica.critica.md')
    juiz.registrar_custo(pasta, juiz.custo(resp, 0, modelo), rotulo='rubrica', status=status)
    print('[rubrica] critica em rubrica.critica.md (%s, %s)' % (modelo, status))
    return 0 if status == 'ok' else 3


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(criticar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else MODELO_PADRAO))
