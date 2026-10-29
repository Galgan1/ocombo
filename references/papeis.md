# Os papeis do combo como subagentes (v10, 10/09/2026)

Quem executa cada lamina deixou de ser "a mesma cabeca com boa vontade" e passou a ser um subagente com
contexto, ferramentas e modelo proprios. Fonte auditada: `references/pesquisa-2026-09-10-v10.md`.

## Quem e quem

| papel | arquivo | modelo | ferramentas | nao pode |
|---|---|---|---|---|
| GRELHA (lamina 1) | `assets/agentes/ocombo-grelha.md` | `sonnet` (v13), effort high | Read/Glob/Grep/Write/Bash/Web/Skill | `Edit`, `NotebookEdit`, abrir subagente |
| EXECUTOR (laminas 3 e 4) | `assets/agentes/ocombo-executor.md` | inherit, effort high | as de trabalho + Edit/Write | julgar-se, tocar veredicto/carimbo |
| JUIZ (lamina 2) | `assets/agentes/ocombo-juiz.md` | `sonnet` (tier != executor) | Read/Glob/Grep/Bash/Skill | `Edit`, `Write`, `NotebookEdit` |

O MAESTRO continua sendo a sessao principal: ele roda a porta, delega, guarda o ledger e leva a regua
de escalada ao dono. Papel nenhum abre subagente (sem `Agent` na allowlist) — a arvore e rasa de
proposito: um juiz por instancia, como manda a secao de paralelismo.

## Instalar (idempotente, versionado pelo canal)

    python scripts/instalar_agentes.py              # copia para ~/.claude/agents
    python scripts/instalar_agentes.py --verificar  # exit 1 se faltar ou divergir (portao)

Os arquivos moram na skill; `~/.claude/agents/` e destino, nunca fonte. Editou o
papel? Edite em `assets/agentes/` e instale de novo — `--verificar` acusa quem editou o destino.

## Como delegar

- Grelha: `Agent(subagent_type="ocombo-grelha")` com o pedido cru + a pasta da instancia + as palavras
  para o `decisoes.py`. Volta: caminho do `solucao.txt`, decisoes tomadas, `[DONO]` no ledger.
- Executor: `Agent(subagent_type="ocombo-executor")` com o caminho do `solucao.txt`. Ele le o ESTADO,
  nao a conversa.
- Juiz: `Agent(subagent_type="ocombo-juiz")` com o caminho da instancia. Ele roda `juiz.py` — o USD
  medido sai de la, nao da leitura dele.

Executor e juiz nunca rodam na mesma delegacao. Se o juiz reprovou, quem ajusta e o executor, numa
delegacao nova, com o veredicto como entrada.

## Limite honesto

`Bash` grava arquivo (`sed -i`), e o juiz precisa de `Bash` para rodar `juiz.py`. Entao "quem julga nao
conserta" e sustentado por tres coisas parciais, e nao por uma prova: allowlist sem `Edit`/`Write`,
regra no prompt do papel, e o carimbo `aprovado.sha256` que acusa plano alterado depois do julgamento.
Quem quiser fechar o resto instala um hook `PreToolUse` de projeto barrando escrita quando o agente for
o juiz (`references/hooks.md`); enquanto nao existir, fica escrito aqui que nao esta provado.

## O que a v10 NAO mudou

Piso igual: `prova.bat`, triagem, linter, regua de escalada e carimbo valem em todos os modos e com
todos os papeis. Cross-model continua sendo regra (o `juiz.py` e quem escolhe o modelo por modo; o
`model: sonnet` do papel e o piso de quando o julgamento for a mao). O `solucao.txt` continua sendo a
fonte unica — subagente nao herda a conversa, e e exatamente por isso que ele funciona.

## v12 (29/09/2026): o executor troca de disciplina pelo pacote

O papel e o mesmo; a disciplina muda com a natureza do trabalho. Quando o ESTADO traz a linha
`Pacote       : <tipo> (ler references/pacotes/<tipo>.md)` (gravada pelo `iniciar.py` nos tipos texto,
pesquisa, desenho e acao), o executor le `references/pacotes/<tipo>.md` no passo 0 e os passos 2 e 3 do
`ocombo-executor.md` viram os do pacote: portao escrito ANTES da peca com o vermelho provado, e prova do
jeito que o pacote define. Sem a linha, tudo como hoje (pacote `references/pacotes/codigo.md`). A grelha
ganhou uma linha: fora de codigo usa a regua do pacote, e gosto vai para [LEITURA], nunca finge ser
binario. O juiz nao mudou (`ocombo-juiz.md` intacto) e os nomes das laminas `akita` e `producao-senior`
tambem nao.

## v13 (02/10/2026): a grelha vai para o Sonnet 5.5; o executor fica na sessao

Ordem do dono em 01/10/2026 (ciclo de um projeto): "utilize sonnet 5.5 nos subagentes." e "inverta opus por sonnet."
Leitura aplicada: o executor e a sessao principal (Opus 5.5 ou Fable 5.1 — ele mesmo faz a lamina 3, ou delega ao
`ocombo-executor`, que herda a sessao); juiz e demais subagentes em Sonnet 5.5. Por isso `ocombo-grelha.md` passou
de `inherit` para `model: sonnet` e `ocombo-executor.md` continua `inherit` de proposito: executor em Sonnet obrigaria
o juiz a subir para Opus (cross-model) e o juiz e a rodada cara. `instalar_agentes.py --verificar` exit 0 em 02/10/2026.
Limite honesto: a grelha em Sonnet escreve a rubrica que o juiz Sonnet vai usar — o `rubrica.py` (Haiku) critica a
rubrica antes, e um ciclo real em tipo `skill` ainda nao comparou grelha Sonnet x grelha na sessao; medir, nao supor.
