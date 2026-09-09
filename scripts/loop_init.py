# -*- coding: utf-8 -*-
"""Instalador UNIVERSAL do loop-agente.

Roda em QUALQUER pasta e gera ali uma INSTÂNCIA isolada do loop:
pontes (.bat) + contrato próprios. Cada pasta vira um loop independente,
com seus próprios solucao.txt / veredicto.md / historico_loop.log — sem
colidir com outras instâncias.

Uso:
    python loop_init.py            # instala na pasta atual (cwd)
    python loop_init.py <pasta>    # instala na pasta indicada

Idempotente: sobrescreve as pontes (código), mas NUNCA apaga solucao.txt,
veredicto.md ou o log (dados da instância).
"""
import os
import sys

VERIFICAR_BAT = r'''@echo off
REM Loop Verifier (Config C) - instancia local nesta pasta.
REM Antigravity escreve solucao.txt; roda este bat; Claude (Opus) julga -> veredicto.md
cd /d "%~dp0"
if not exist solucao.txt (
  echo [erro] solucao.txt nao encontrado em %cd%
  exit /b 1
)
if exist veredicto.md del veredicto.md
set "CLAUDE=claude"
where claude >nul 2>nul || set "CLAUDE=%APPDATA%\npm\claude.cmd"
call "%CLAUDE%" -p "Voce e o VERIFIER do loop (cross-model). Use a skill loop-agente. Leia solucao.txt nesta pasta (tarefa + rubrica + solucao). NAO execute a tarefa; JULGUE cada criterio da rubrica PASS/FAIL com motivo (a critica vem ANTES). Se existir prova.bat, o exit code dela ja e o gate duro - julgue so o que o teste nao pega (escopo, estilo, pt-BR). Termine com UMA linha exatamente: VEREDICTO: APROVADO  ou  VEREDICTO: AJUSTE (nunca REPROVADO nem NAO APROVADO); se AJUSTE, inclua follow-up cirurgico. Escreva veredicto.md, sobrescrevendo. Nao peca confirmacao." --model claude-opus-5 --permission-mode acceptEdits < nul
if not exist veredicto.md (
  echo [erro] Claude falhou em gerar veredicto.md
  echo %date% %time% - ERRO >> historico_loop.log
  exit /b 1
)
findstr /i /c:"VEREDICTO: APROVADO" veredicto.md >nul && (
  echo %date% %time% - APROVADO >> historico_loop.log
  goto :done
)
echo %date% %time% - AJUSTE >> historico_loop.log
:done
echo.
echo [ok] veredicto.md gerado nesta pasta.
'''

EMULAR_BAT = r'''@echo off
REM Emulador cross-model: juiz != autor (opus ^<-^> sonnet).
REM Uso: emular_verificador.bat ^<modelo^>   (ex.: claude-sonnet-5)
cd /d "%~dp0"
set "VMODEL=%~1"
if "%VMODEL%"=="" set "VMODEL=claude-sonnet-5"
if not exist solucao.txt (
  echo [erro] solucao.txt nao encontrado em %cd%
  exit /b 1
)
if exist veredicto.md del veredicto.md
set "CLAUDE=claude"
where claude >nul 2>nul || set "CLAUDE=%APPDATA%\npm\claude.cmd"
call "%CLAUDE%" -p "Voce e o VERIFIER do loop (cross-model, juiz != autor). Use a skill loop-agente. Leia solucao.txt; NAO execute a tarefa; JULGUE cada criterio da rubrica PASS/FAIL com motivo (a critica vem ANTES). Se existir prova.bat, o exit code dela e o gate duro - julgue so o que o teste nao pega. Termine com UMA linha exatamente: VEREDICTO: APROVADO  ou  VEREDICTO: AJUSTE (nunca REPROVADO nem NAO APROVADO); se AJUSTE, follow-up cirurgico. Escreva veredicto.md, sobrescrevendo. Nao peca confirmacao." --model %VMODEL% --permission-mode acceptEdits < nul
if not exist veredicto.md (
  echo [erro] Verificador %VMODEL% falhou em gerar veredicto.md
  exit /b 1
)
echo.
echo [ok] veredicto.md gerado pelo verificador cross-model %VMODEL%
'''

VENCI_BAT = r'''@echo off
cd /d "%~dp0"
if exist veredicto.md del veredicto.md
call "%~dp0verificar.bat"
'''

EXECUTAR_BAT = r'''@echo off
REM Subagente EXECUTOR - produz solucao.txt a partir de spec.txt (nesta pasta).
REM Uso: executar.bat <modelo_executor>   (default opus)
cd /d "%~dp0"
set "XMODEL=%~1"
if "%XMODEL%"=="" set "XMODEL=claude-opus-5"
if not exist spec.txt (
  echo [erro] spec.txt nao encontrado em %cd%
  exit /b 1
)
set "CLAUDE=claude"
where claude >nul 2>nul || set "CLAUDE=%APPDATA%\npm\claude.cmd"
call "%CLAUDE%" -p "Voce e o SUBAGENTE EXECUTOR descrito em spec.txt nesta pasta. Leia spec.txt (papel, objetivo, contexto, resultado esperado, rubrica). Se existir veredicto.md, e follow-up de prioridade maxima - corrija so o que falhou. Mantenha-se no escopo. Se existir prova.bat nesta pasta, ela e o GATE DURO (verde = exit code 0) - produza a solucao para passar nela. Produza a solucao e escreva solucao.txt contendo: a TAREFA e a RUBRICA copiadas de spec.txt, depois uma linha 'SOLUCAO PRODUZIDA:' e a sua solucao no formato pedido. Sobrescreva solucao.txt. Nao peca confirmacao." --model %XMODEL% --permission-mode acceptEdits < nul
if not exist solucao.txt (
  echo [erro] executor %XMODEL% nao gerou solucao.txt
  exit /b 1
)
echo [ok] solucao.txt gerado pelo executor %XMODEL%
'''

SPEC_TEMPLATE = '''# Subagente: (nome)
PAPEL: (quem o subagente deve ser)
OBJETIVO: (o que produzir)
CONTEXTO/FONTES: (dados necessarios)
RESULTADO ESPERADO: (formato do output, ex.: JSON)

TAREFA: (a tarefa concreta)

RÚBRICA:
[ ] criterio 1 (objetivo, PASS/FAIL)
[ ] criterio 2
'''

CONTRATO_MD = '''# Contrato do Loop (instância local) — Antigravity (Planner+Executor) ↔ Claude (VERIFIER)

Esta pasta é uma **instância isolada** do loop-agente. Tudo aqui é local: as pontes e os arquivos `solucao.txt` / `veredicto.md` / `historico_loop.log` desta pasta não colidem com outras instâncias.

## Papéis
- **Antigravity = PLANNER + EXECUTOR + controle do loop.** Decompõe, produz a solução, conta as tentativas.
- **Claude = VERIFIER.** Só julga a solução contra a rúbrica. Chamado por `verificar.bat`.
- **Canal = arquivos NESTA pasta.** Sem porta; só o Antigravity chama pra fora.

## Os 2 arquivos (locais a esta pasta)
| Arquivo | Quem escreve | Conteúdo |
|---|---|---|
| `solucao.txt` | Antigravity | tarefa + rúbrica + a solução produzida |
| `veredicto.md` | Claude (Verifier) | PASS/FAIL item a item + APROVADO/AJUSTE + follow-up |

## Ciclo (máx. 5 tentativas)
1. PLANNER: defina a rúbrica (critérios PASS/FAIL).
2. EXECUTOR: produza a solução.
3. Escreva `solucao.txt` (tarefa + rúbrica + solução). Rode `verificar.bat` (ou `venci.bat`).
4. Leia `veredicto.md`: APROVADO → fim; AJUSTE → corrija só o que falhou, reescreva `solucao.txt`, repita.
5. Parada: 5 tentativas.

## Pontes desta instância
- `verificar.bat` — Claude **Opus** como Verifier (uso normal, junto ao Antigravity-Gemini = já é cross-model).
- `emular_verificador.bat <modelo>` — emulador cross-model quando NÃO há Antigravity (juiz ≠ autor: Opus↔Sonnet).
- `venci.bat` — atalho: limpa `veredicto.md` e roda `verificar.bat`.
'''

SOLUCAO_TEMPLATE = '''TAREFA: (descreva aqui o que deve ser feito)

RÚBRICA:
[ ] criterio 1 (objetivo, PASS/FAIL)
[ ] criterio 2
[ ] criterio 3

SOLUÇÃO PRODUZIDA:
(cole aqui a solução a ser julgada)
'''

PROVA_EXEMPLO = r'''@echo off
REM PROVA EXECUTAVEL (Akita: verde = exit code). COPIE este arquivo para prova.bat e ajuste.
REM O loop roda prova.bat ANTES do juiz: exit 0 = gate verde; !=0 = AJUSTE automatico
REM (a saida e reinjetada no executor como follow-up). O juiz so cobre o que o teste nao pega.
cd /d "%~dp0"
REM >>> troque a linha abaixo pelo comando que VALIDA a tarefa (o exit code vira o veredito) <<<
python testar.py
'''

# (código, sempre sobrescreve) ; (dado, só cria se não existir)
KIT_CODE = {
    'verificar.bat': VERIFICAR_BAT,
    'emular_verificador.bat': EMULAR_BAT,
    'executar.bat': EXECUTAR_BAT,
    'venci.bat': VENCI_BAT,
    'prova.exemplo.bat': PROVA_EXEMPLO,
    'CONTRATO.md': CONTRATO_MD,
}
KIT_DATA = {
    'solucao.txt': SOLUCAO_TEMPLATE,
    'spec.txt': SPEC_TEMPLATE,
}


def instalar(destino):
    destino = os.path.abspath(destino)
    os.makedirs(destino, exist_ok=True)
    for nome, conteudo in KIT_CODE.items():
        # .bat com CRLF (cmd); .md tanto faz
        nl = '\r\n' if nome.endswith('.bat') else '\n'
        with open(os.path.join(destino, nome), 'w', encoding='utf-8', newline=nl) as f:
            f.write(conteudo)
        print(f'  [code] {nome}')
    for nome, conteudo in KIT_DATA.items():
        caminho = os.path.join(destino, nome)
        if os.path.exists(caminho):
            print(f'  [skip] {nome} (ja existe, preservado)')
        else:
            with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
                f.write(conteudo)
            print(f'  [data] {nome} (template)')
    print(f'\nInstancia do loop-agente criada em:\n  {destino}')
    print('Uso: edite solucao.txt e rode  venci.bat  (ou emular_verificador.bat claude-sonnet-5)')


if __name__ == '__main__':
    alvo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    instalar(alvo)
