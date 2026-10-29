# Ferramentas da esteira — referência dos scripts (ocombo v3, 05/09/2026)

Tudo em `scripts/` da skill; testes puros em `test_juiz.py`, `test_v3.py`, `test_hook.py`, `test_qualidade.py`, `test_ledger.py`, `test_modos.py` (nunca chamam
`claude`, ruff, eslint nem playwright); o portão `prova.py` na raiz da skill roda todos. Caminho base:
`<skill>/scripts/` (na casa, `~/.claude/skills/ocombo/scripts/`). Fontes auditadas por versão: `references/pesquisa-2026-09-05.md` (v2),
`references/pesquisa-2026-09-05-v3.md` (v3), `references/pesquisa-2026-09-06-v4.md` (v4), `references/pesquisa-2026-09-06-v6.md` (v6).

| script | para quê | custo |
|---|---|---|
| `iniciar.py <pasta> [--tipo T] [--palavras p…]` | abre a instância num comando: loop_init + solucao.txt (modelo + rúbrica do tipo + decisões herdadas) + evidencias/ corpus/ prova.bat | 0 |
| `modos.py [0..10|f1]` | os 12 perfis do combo (v9): quanto investir acima do piso. Sem argumento imprime a tabela; `perfil()` le `OCOMBO_MODO`; `validar_effort` barra valor que a CLI aceitaria calado; `turbo()` liga o fast mode e a escalada de dinheiro. Nenhum perfil mexe em `PORTOES` | 0 |
| `loop_init.py [pasta]` | instalador do loop (pontes `.bat` + contrato) que o `iniciar.py` chama; embarcado na v7 (07/09/2026) — `OCOMBO_LOOP_INIT` aponta outro se quiser | 0 |
| `decisoes.py <palavras> [--memoria dir]` | grep nas memórias por linhas com marcador de decisão + palavra-chave → rascunho do contexto herdado | 0 |
| `rubrica.py <pasta> [modelo]` | modelo barato critica SÓ a RUBRICA antes da rodada 1 → `rubrica.critica.md` | Haiku, centavos |
| `triagem.py <pasta>` | checagem determinística da forma (ESTADO, RUBRICA numerada + REGRESSÃO, SOLUÇÃO, caminhos citados existem) + `manifesto.txt` | 0 |
| `juiz.py <pasta> [modelo] [--timeout s] [--effort e]` | v16 (26/10/2026, "esqueça gemini"): o padrão e todos os modos julgam com o `claude-sonnet-5-5`; o agy só roda com id `agy:` explícito. v15: modelo `agy:<id>` = Antigravity CLI oficial como juiz (fila de cota, `--add-dir` das raízes citadas, cópias em `historico/leitura/`, tripwire, veredicto pelo `response`, INDEFINIDO por cota/permissão/violação); `OCOMBO_JUIZ_CLAUDE=1` volta ao `claude -p` byte a byte. prova.bat → triagem → snapshot/delta/manifesto → juiz cross-model → veredicto.md + custo.log (+ histórico global); APROVADO grava `aprovado.sha256` (v6) e a rodada seguinte julga FAIL + N/A | Sonnet 5.5 por padrão; `--effort` explícito vence o do modo (v13) |
| `OCOMBO_CAVEMAN=off\|lite\|full\|ultra` (env) | v8 (07/09/2026): estilo da CRÍTICA do juiz (e da dupla, que herda o prompt) — regras da skill `caveman` embutidas em `juiz.CAVEMAN`; padrão `full`; `off` volta à prosa antiga; `CRITERIO`/`VEREDICTO` e o follow-up de FAIL nunca são comprimidos. Medição A/B na seção "Caveman no juiz" | 0 |
| `juiz.py --carimbo <pasta>` | v6: confere o carimbo contra o sha256 atual do solucao.txt — exit 0 válido, 1 CADUCOU (plano mudou depois do APROVADO), 2 nunca aprovado | 0 |
| `dupla.py <pasta> <modeloB>` | segundo juiz sobre o MESMO estado → `veredicto.<modeloB>.md` + `concordancia.md` (+ v6: linhas "B a favor / contra o executor" e evento `dupla` no ledger) | modelo B |
| `dupla.py --balanco` | v6: últimos 10 ciclos com dupla — quantas vezes o Opus aprovou o que o Sonnet reprovou; exit 1 acima de 3 = levar ao dono a troca do juiz padrão | 0 |
| `custo_historico.py [log]` | tabela por instância (rodadas, USD, USD/rodada, s) a partir de `~/.claude/ocombo-custo.log`; `--modelos` = média por modelo × papel × effort (v13) | 0 |
| `prova_hook_vivo.py [modelo]` | prova ao vivo do hook Stop num projeto temporário via `claude -p --settings` | Haiku, centavos |
| `qualidade.py <repo> [--saida f] [--so py\|js]` | linter de correção (ruff F/E9 + eslint no-undef/no-unused-vars, config fixa em assets/, ESM pelo package.json, pula bundle minificado) → relatório por regra + `EXIT=`; exit 1 = AJUSTE sem juiz | 0 |
| `smoke_web.py <url> [--texto T] [--seletor css] [--saida f]` | smoke de navegador: copia assets/playwright/ para a pasta com `@playwright/test` (repo ou `OCOMBO_NODE_TOOLS`), abre a URL no Chromium headless, falha com erro de JS, 5xx ou texto ausente → `EXIT=` | 0 |
| `ledger.py escalar\|sim\|pendentes\|resumo\|veredicto ...` | ledger da regua de escalada em `~/.claude/ocombo-ledger.jsonl` (local): escalada aberta = esteira para naquele passo; `pendentes` exit 1 e portao; `resumo [dia]` = cupom de 40 colunas; o juiz.py grava cada veredicto sozinho | 0 |

## Rito completo de um ciclo

```
python scripts/iniciar.py <pasta> --tipo bot --palavras whatsapp allowlist   # 1 comando
(editar solucao.txt: TAREFA, ajustar RUBRICA, herdado)
python scripts/rubrica.py <pasta>                                            # crítica da régua (Haiku)
(acatar o que vale; declarar na SOLUÇÃO o que não acatou)
python scripts/juiz.py <pasta>                                               # rodada 1 (lê tudo)
... corrigir só o FAIL, atualizar ESTADO ...
python scripts/juiz.py <pasta>                                               # rodada N (só o diff)
python scripts/dupla.py <pasta> claude-opus-5-5                                # carimbo da ENTREGA (opcional / "extra")
python scripts/custo_historico.py                                            # quanto custou, comparado aos outros ciclos
python scripts/custo_historico.py --modelos                                  # v13: média por modelo x papel x effort (tier e effort por medida)
```

## Saídas e códigos

- `juiz.py`: exit 0 APROVADO · 1 AJUSTE (inclui prova vermelha e triagem, sem tokens) · 2 erro de uso ·
  3 INDEFINIDO (timeout 2× — repita ou troque o modelo; não é culpa do executor).
- `custo.log` (instância) e `~/.claude/ocombo-custo.log` (global, com o nome da instância). Rótulos:
  `rN`, `rubrica`, `dupla`; status `timeout` ou `... juiz nao chamado (0 tokens)`.
- `historico/solucao.rN.txt`, `historico/veredicto.rN.md`, `delta.patch`, `manifesto.txt`, `rubrica.critica.md`,
  `veredicto.<modeloB>.md`, `concordancia.md`, `aprovado.sha256` (v6; só existe enquanto o último veredicto é APROVADO).

## Banco de rúbricas (`assets/rubricas/`)

`bot.txt`, `site.txt`, `script-agendado.txt`, `receita-maquina.txt`, `skill.txt` — critérios binários
nascidos das armadilhas desta casa; todo arquivo termina com o critério de REGRESSÃO. `iniciar.py --tipo`
cola o arquivo do tipo na RUBRICA; o executor adapta ao caso (e o `rubrica.py` critica o resultado).

## Hooks (o dono instala por projeto)

`assets/hooks.exemplo.json` + `assets/portao-hook.py`. Variáveis: `OCOMBO_PORTAO` (comando do portão,
padrão `python prova.py`), `OCOMBO_HOOK_LOG` (arquivo onde cada disparo grava `<modo> <exit>`). Para uma
execução só: `claude --settings hooks.json` (a doc: "Values you set here override the same keys … for this
session"; hooks se somam aos de `~/.claude`). `--bare` desliga hooks.

## Limites conhecidos

- O juiz `claude -p` roda em sandbox e NÃO lê fora da pasta da instância: copie o corpus para dentro e
  prove "cópia fiel" por sha256 dos dois lados.
- Matar o `claude -p` por fora (timeout) dá exit 143 sem `result` e sem hook Stop — por isso o `juiz.py`
  registra `timeout` e escreve INDEFINIDO, em vez de fingir veredicto.
- `dupla.py` mede concordância por critério em percentual; com poucos critérios o número é grosseiro
  (a literatura prefere κ/π) — use para achar critério ambíguo, não para "nota" do juiz.

## Ferramentas de teste (v4)

- `assets/eslint.config.base.mjs` — config fixa do `qualidade.py` (sem import de pacote; `OCOMBO_ESLINT_MODULE` liga ESM).
- `assets/playwright/smoke.spec.js` + `assets/playwright/playwright.config.js` — smoke de navegador; o `smoke_web.py` copia os dois para `<pasta com node_modules>/ocombo-smoke/` e roda `npx playwright test` ali.
- Variavel `OCOMBO_NODE_TOOLS`: pasta com `node_modules` de eslint/@playwright/test quando o repo nao tem os seus.
- Mutacao provada em 06/09/2026: pagina com `throw new Error` -> EXIT=1; sandbox do painel interno -> EXIT=0.

## Espelho público (v7, 07/09/2026)

A skill é publicada em `github.com/Galgan1/ocombo` (MIT) por `tools/publicar.py` do próprio repo: copia
SKILL.md, prova.py, scripts/, assets/ e references/ da casa, normaliza LF e aplica um mapa LOCAL de
substituições (`~/.claude/ocombo-publicar.json`, fora do repo e fora do canal) que troca nomes de projetos
e pessoas da casa por termos genéricos. `tools/prova_repo.py` é o portão do repo (roda `prova.py` da skill e
reprova caminho de máquina, telefone, e-mail, CPF, token e termo privado); a CI roda o mesmo no Ubuntu e no
Windows. Republicar = `python tools/publicar.py` (exit 0) → `git commit` → `git push`; `--checar` só compara.
No POSIX o juiz roda `prova.sh` da instância no lugar de `prova.bat` (`juiz.comando_prova`).

## Caveman no juiz (v8, 07/09/2026) — medido, não sentido

Ordem do dono: "coloca o caveman no juiz do ocombo". As regras da skill `caveman` (nível full: sem artigos, sem
cortesia, sem hedge, sem narração de ferramenta, cada fato uma vez; NUNCA cortar não/nunca/só/exceto; números,
arquivos, comandos e erros exatos; português) foram embutidas no prompt do juiz (`juiz.CAVEMAN`), com guarda: as
linhas `CRITERIO`/`VEREDICTO` ficam no formato exato e o follow-up de FAIL volta à prosa clara (auto-clareza da
própria skill). `OCOMBO_CAVEMAN=off` volta ao prompt anterior; `lite`/`ultra` existem. A `dupla.py` herda.

A/B no MESMO estado (instância ocombo-visibilidade, Sonnet 5, rodada 1 completa nas duas):

| | tokens de saída | USD | s | palavras do veredicto | resultado |
|---|---|---|---|---|---|
| A sem caveman | 8.350 | 0,298 | 94 | 410 | APROVADO 6/6 |
| B caveman full | 7.580 | 0,288 | 90 | 422 | AJUSTE (C2 FAIL) |

Leitura honesta: a economia foi de 9% nos tokens de saída e 3% no custo — o gordo da saída do juiz é o uso de
ferramenta (abrir arquivos, 8 turnos), não a prosa; o prompt mais denso não encurtou o veredicto em palavras. O que
mudou de verdade foi a CRÍTICA: o juiz caveman achou um furo real que o juiz normal tinha deixado passar (a busca
"Todos os e-mails" do Gmail não cobre Spam nem Lixeira), e o follow-up veio em prosa clara como a guarda pede. Fica
como padrão pela crítica mais seca e verificável, não pela economia. Repetir a medição em ciclo maior (rodada de
30 mil tokens de saída) antes de prometer número.

Tabela dos modos em `references/modos.md`; fontes auditadas da v9 em `references/pesquisa-2026-09-09-v9.md`.

## Smoke de navegador: o filtro de sessao (10/09/2026)

`assets/playwright/smoke.spec.js` contava QUALQUER `console.error` como erro de JS. Toda tela de login com sessao por cookie chama `/api/me`, toma 401 e o navegador loga `Failed to load resource: the server responded with a status of 401` — ou seja, o smoke reprovava a tela de entrada de qualquer sistema. Achado por outra sessao ao publicar um painel interno.

`assets/playwright/filtro.js` separa RELATO de request (do navegador) de ERRO de JS. `SMOKE_IGNORAR_STATUS` (padrao `401,403`) diz quais status de sessao nao contam; lista vazia devolve o rigor total; **5xx nunca se tolera** e excecao de JS (`pageerror`) sempre conta. O spec imprime o que ignorou, entao o relatorio nunca fica mudo. Testes: `node assets/playwright/test_filtro.js` (6 casos, sem Playwright e sem rede), no `prova.py`.

Prova ao vivo, com servidor local que imita tela de login (10/09/2026): pagina com 401 de sessao -> EXIT=0 e a linha `[smoke] 1 relato(s) de sessao ignorado(s)`; a MESMA pagina com `SMOKE_IGNORAR_STATUS=` vazio -> falha; pagina com erro de JS de verdade -> falha. O filtro nao cega o teste, so para de reprovar o que nao e defeito.

## v10 (10/09/2026): a porta e os papeis

`scripts/porta.py` — decide QUAIS laminas rodam antes de gastar a primeira ficha. Entrada por fato
declarado (`--reparo/--novo`, `--arquivos N`, `--regua`, `--decisoes-abertas`, `--criterio-de-pronto`);
as palavras do pedido apenas PRE-preenchem (`porta.pistas`, sem acento). Saida: as tres linhas do
ESTADO (Porta / Laminas / Papeis) ou `--json`. Exit 2 = ordem invalida: `--forcar sem-grelha` num
pedido que toca a regua de escalada e recusado, porque portao nao se desliga por ordem.

`scripts/instalar_agentes.py` — instala `assets/agentes/ocombo-grelha.md`, `ocombo-executor.md` e
`ocombo-juiz.md` em `~/.claude/agents` (idempotente). `--verificar` sai 1 quando falta arquivo, o
destino divergiu ou o papel esta invalido: name != nome do arquivo, description curta demais para
dizer QUANDO delegar, juiz com ferramenta de escrita (`Edit`/`Write`/`NotebookEdit`), juiz com
`model: inherit` (mataria o cross-model) ou papel com `Agent` na allowlist (arvore de subagente rasa).

`scripts/test_papeis.py` — 18 testes puros das duas pecas (sem `claude`, sem rede, destino em tmpdir),
dentro do `prova.py`. Doutrina e limite honesto em `references/papeis.md`; fontes auditadas em
`references/pesquisa-2026-09-10-v10.md`.

## v11 (20/09/2026): o sommelier por tarefa

`scripts/sommelier.py` — modelo e effort por CLASSE de tarefa de um fan-out (tabela pura, sem `claude`
e sem rede). `--tarefa C --agentes N`, `--plano "classe:n,classe:n"` (imprime a linha `Sommelier:` do
ESTADO e o custo relativo ao tudo-no-topo; `--tokens entrada,saida` da o USD de tabela para volume
medido) e `--checar "classe:n=alias"`. Exit 0 ok | 1 erro de uso (classe, alias, modo ou plano
invalido) | 2 plano RECUSADO: lote no tier de topo (regua de dinheiro) ou conferente no tier do autor
(quebra o cross-model). Le `OCOMBO_MODO` e `OCOMBO_SESSAO`; reusa `modos.perfil` e `modos.validar_effort`.

`scripts/test_sommelier.py` — 30 testes puros, dentro do `prova.py`: a regra "lote nunca no topo"
varrida em 8 classes x 12 modos x 4 sessoes x 4 tamanhos, o cross-model do conferente, a premissa do
custo relativo (saida = 5x entrada em todo tier) e os tres exit codes da CLI. Doutrina, incidente de
origem e limites em `references/sommelier.md`.

`scripts/fecho_fable.py <instancia>` — ordem do dono (03/10/2026): no fim das rodadas o Fable 5.1 no máximo
(`claude-fable-5-1 --effort max`) julga SEMPRE o resultado inteiro, depois do carimbo (`juiz.py --carimbo` exit
0, senão exit 2). ACEITO (exit 0) = ele escreve a mensagem `.441` ao dono (4 parágrafos de 36 a 44 palavras,
sem custo), gravada em `fecho.md`; REFAZER (exit 1) = MOTIVOS numerados, o combo roda só sobre eles e chama o
fecho de novo; teto 3 julgamentos (`historico/fecho.rN.md`; o 4º sai exit 3 = parada honesta ao dono);
INDEFINIDO (exit 4) = resposta sem `FECHO:` válido ou mensagem fora da forma, não conta no teto. Grava
custo.log e uma linha no ledger. Não substitui o juiz cross-model das rodadas: é o último olhar.
`scripts/test_fecho.py` — 13 testes puros (sem chamar `claude`): modelo e effort fixos, leitura de
ACEITO/REFAZER/INDEFINIDO, forma `.441` com tolerância de 10%, custo proibido, contador e teto.

## v12 (29/09/2026): pacotes por natureza

`scripts/iniciar.py --tipo texto|pesquisa|desenho|acao` — os 4 tipos novos (`TIPOS_PACOTE`) colam a regua do
tipo e passam pela funcao pura `aplicar_pacote(texto, tipo)`: linha `Pacote       : <tipo> (ler
references/pacotes/<tipo>.md)` logo depois de `Papeis` e `Lamina atual` reescrita para `[grelha | juiz |
akita=portao antes da peca | producao so se a regua pedir]`. Nos 5 tipos de codigo (`TIPOS_CODIGO`) e em
tipo desconhecido ela devolve o texto intacto; padrao continua `skill`; tipo invalido continua exit 2.
Testes na classe `TestPacotesV12` do `scripts/test_v3.py` (dentro do `prova.py`).

Reguas novas (mesmo formato das antigas: C0 CONFORMIDADE, ESCALADA, SOMMELIER, REGRESSAO por ultimo; todo
criterio de qualidade [MEDIDO] com comando e exit code, ou [LEITURA] com segundo leitor de outro tier
citando a linha, no maximo 1/3): `assets/rubricas/texto.txt`, `assets/rubricas/pesquisa.txt`,
`assets/rubricas/desenho.txt`, `assets/rubricas/acao.txt`.

Pacotes (o que as laminas 3 e 4 viram, o que conta como prova, `prova.bat` tipico, pedido misto,
armadilhas medidas): `references/pacotes/codigo.md` (as 5 reguas antigas e o corpo de "Ferramentas de
teste" que saiu do SKILL.md), `references/pacotes/texto.md`, `references/pacotes/pesquisa.md`,
`references/pacotes/desenho.md`, `references/pacotes/acao.md`. Changelog e o que saiu do SKILL.md em
`references/versoes.md` (v12).

## v14 (04/10/2026): a regra da RAM livre

- `scripts/ram.py` — imprime `RAM livre   : N MB -> vagas K, ...` (linha do ESTADO); `vagas = (livre - 1500) // 750`,
  entre 1 e 4. Uma vaga = um `claude -p` (juiz, dupla, fecho) ou um critério pesado do portão. Testes: `scripts/test_ram.py`.
- `assets/mcp-vazio.json` — com `OCOMBO_SEM_MCP=1` o `juiz.py` (e dupla/rubrica/fecho, que usam `argumentos_claude`)
  sobe com `--strict-mcp-config --mcp-config assets/mcp-vazio.json`. Sem a variável, a linha é byte a byte a de antes.

## Pesquisas auditadas (fonte de toda URL do SKILL.md)

`pesquisa-2026-09-05.md`, `pesquisa-2026-09-05-v3.md`, `pesquisa-2026-09-06-v4.md`, `pesquisa-2026-09-06-v6.md`,
`pesquisa-2026-09-09-v9.md`, `pesquisa-2026-09-10-v10.md` e, na v13, `pesquisa-2026-10-02-v13.md` (tabela de modelos e
preços de 25/09/2026, trechos literais da doc sobre effort, e a medição do custo.log por modelo e papel).
