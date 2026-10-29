---
name: ocombo
description: >-
  Esteira completa da casa para entregar qualquer trabalho (sistema, texto, pesquisa, desenho, ação):
  grelha auto-respondida, juiz de outra família por diff, TDD com portão único e régua de escalada
  (dinheiro, produção, apagar, terceiro, decisão do dono). Use quando o dono disser "/ocombo", "o combo",
  "usa o combo", "faz pelo sistema completo" ou "coloca no ar com o sistema", pedir projeto entregue com
  juiz sem parar no meio, ou escolher um modo (0 a 10, "opala", F1), e antes de todo fan-out de 3+ agentes.
  Mensagem avulsa é da skill editor.
---

# O COMBO — grelha → juiz → TDD → produção, sem parar no meio

A skill é julgada por ela mesma: fonte auditada em `references/pesquisa-*.md`, portão em `prova.py`,
scripts em `references/scripts.md`, changelog em `references/versoes.md`.

## As quatro lâminas, na ordem

1. **`grilling` (/grill-me)** — papel `ocombo-grelha`, e SÓ quando a porta pedir (v10): mapeie a árvore
   de decisões e escreva o QUESTIONÁRIO: perguntas numeradas
   + a SUA resposta recomendada em cada uma. Quando o dono delegar ("responda com as suas sugestões" /
   "sem humano"), as respostas são suas — mas NUNCA reabra decisão que o dono já fechou: cite-a como
   contexto herdado inviolável na TAREFA. Rascunho do herdado: `scripts/decisoes.py <palavras>`.
2. **`loop-agente`** — papel `ocombo-juiz` julga; o questionário vira `solucao.txt` numa INSTÂNCIA própria (`scripts/iniciar.py
   <pasta> --tipo T --modo M` faz tudo num comando), com RÚBRICA binária fixa no topo e a seção ESTADO
   (modelo em `assets/solucao.modelo.txt`). Antes da rodada 1, `scripts/rubrica.py` (Haiku) critica a
   rúbrica. O juiz é `python scripts/juiz.py <instância> [modelo]` — **cross-model sempre** (executor
   Fable/Opus → juiz de outro tier; padrão v16 `claude-sonnet-5-5` em todos os modos: o Gemini saiu do processo em 26/10/2026, ordem do dono "esqueça gemini. registre isto no processo."; o backend agy só roda com um id `agy:` explícito), "extra" = `claude-opus-5-5` ou
   `scripts/dupla.py`); `emular_verificador.bat` é o reserva. Teto de rodadas: o que o modo fixar (padrão
   5); estourou = parada honesta, entrega melhor versão + pendência declarada e PERGUNTA se vale rodada
   extra. Follow-up é cirúrgico: mexa SÓ no que reprovou. APROVADO grava `aprovado.sha256` do plano (v6):
   mudou o `solucao.txt` depois, o carimbo caducou — `juiz.py --carimbo <instância>` exit 0 é portão
   antes da lâmina 3.
3. **`akita`** — papel `ocombo-executor`, só depois do APROVADO: TDD de verdade (prove o VERMELHO antes do módulo), lógica pura
   separada da fiação, arquivos <500 linhas, portão único (`teste.js`/`prova.py`), constituição
   atualizada, um commit por mudança operacional.
   Fora de código, ver `references/pacotes/`: a lâmina vira portão escrito ANTES da peça.
4. **`producao-senior`** — deploy SÓ pelo script com portões; bateria de
   produção com critério novo para cada feature; `portao-publicacao.sh`
   exit 0 antes de publicar; sucesso = exit code e id, nunca opinião;
   incidente NUNCA se maquia — vira teste de regressão + linha no changelog,
   e critério vermelho transitório espera a janela em vez de ganhar exceção.
   Fora de código, ver `references/pacotes/`: entrega fica na instância; terceiro só com "sim".

## Modos — 0 a 10, e o F1 (v9)

Um botão só: o número diz quanto o combo INVESTE acima do piso, nunca o que ele deixa de checar.
**Sem número, é 0** (o combo de sempre, byte a byte). `python scripts/modos.py` lista os 12 perfis; a
tabela, o que cada degrau acrescenta e as armadilhas estão em `references/modos.md`.
Falas do dono que escolhem o modo: "modo 7", "manda no 3", "de opala" (10), "fórmula 1"/"F1", "no talo",
"capricha que é importante" (sobe), "rápido que estou com pressa" (F1).

- **Piso inviolável, igual em todos:** prova da instância, triagem, linter, régua de escalada e carimbo.
  Modo alto compra rodada, esforço e revisor — nunca compra atalho (`modos.PORTOES`, provado por teste).
- **0 a 3** rotina · **4 a 6** trabalho que outra pessoa usa · **7 a 9** dinheiro, produção ou terceiro
  no meio · **10 opala** quando errar custa mais que gastar · **F1** quando o relógio é o problema.
- **10 x F1 são eixos diferentes.** O 10 queima por CERTEZA (pesquisa 4, teto 9, fan-out `size medium` em levas de 4,
  dupla nos passos da régua; desde 29/10/2026 juiz em medium e executor em high, porque effort alto comprava espera,
  não certeza: um diagnóstico interno de 29/10/2026). O F1 queima por TEMPO: paralelo até 16 agentes,
  `CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS=0`, teto 3, juiz Sonnet em effort low, timeout 300 s.
- **Turbo do F1 é dinheiro:** `/fast` sai de "usage credits only and not included in the subscription
  rate limits" (https://code.claude.com/docs/en/fast-mode) — só com o "sim" do dono, régua v5.
- **Onde vive:** `OCOMBO_MODO=7`, `iniciar.py --modo 7|f1` (grava no ESTADO), `juiz.py` lê o perfil
  sozinho; explícito vence o modo, o modo vence o padrão — `juiz.py <pasta> [modelo] [--timeout s]
  [--effort e]` (v13). **Effort é lista fechada** (`low|medium|high|xhigh|max`): a CLI IGNORA valor errado
  com um aviso e roda assim mesmo (medido, USD 0,47), então `modos.validar_effort` levanta antes de montar a chamada.
- **Dose e escada (v13, 02/10/2026):** `--modo 3+`, `3+2`, `7-` sobem ou descem degraus (`modos.ajustar`; f1
  não tem). `iniciar.py --escada` grava `escada: sim` no plano (ou `OCOMBO_ESCADA=1`): começa barato e sobe 1
  degrau por rodada AJUSTE, até 3 acima da partida, nunca sozinha ao 10 nem ao f1 (`modos.escalar`). Sem os
  dois, byte a byte como antes.
- **Medir antes de trocar tier ou effort:** `custo_historico.py --modelos` (média por modelo × papel × effort do
  log local) e um ciclo real comparado. Geração anterior NÃO é mais barata: na tabela de 25/09/2026 Opus 4.8,
  Opus 5 e Sonnet 4.6 custam mais que Opus 5.5 e Sonnet 5.5 (`references/sommelier.md`).

## Ferramentas da esteira (v3) — uma linha cada, detalhe em references/scripts.md

- `iniciar.py` — um comando abre a instância (loop_init + solucao.txt com a rúbrica do tipo +
  decisões herdadas + evidencias/ corpus/ prova.bat).
- `decisoes.py` — decisões fechadas puxadas da memória por grep (markdown + grep, sem RAG — Akita).
  Reabrir decisão do dono é o erro mais caro do combo.
- `rubrica.py` — modelo barato critica a régua ANTES do julgamento: fecha o ponto cego de "quem escreve
  a rúbrica é quem será julgado por ela". Rúbrica vaga "can reward polished answers that invent facts"
  (https://arxiv.org/abs/2605.30803); a Anthropic pede critério "Empirical or specific" e "a different
  model to evaluate" (https://platform.claude.com/docs/en/test-and-evaluate/develop-tests).
- `triagem.py` — checagem determinística da forma antes do juiz (0 tokens): ESTADO, RUBRICA numerada
  com REGRESSÃO, SOLUÇÃO, caminhos citados existem. A cascata barata "caught roughly 60% of failures
  the judge would have caught" (https://futureagi.com/blog/how-i-built-deterministic-llm-evaluation-metrics-2026/).
  Gera `manifesto.txt` (caminho, bytes, sha256) — o juiz abre só o que a SOLUÇÃO cita.
- `juiz.py` — prova.bat → triagem → snapshot/delta/manifesto → juiz com
  timeout (900 s, 1 repetição; 2× = INDEFINIDO, nunca AJUSTE) → veredicto +
  custo.log + histórico global. Matar o `claude -p` por fora dá "exit code
  143 … records no result" (https://code.claude.com/docs/en/headless). v8 (07/09/2026): a crítica sai em modo caveman (regras da skill `caveman` embutidas no prompt; `OCOMBO_CAVEMAN=off|lite|full|ultra`, padrão full); `CRITERIO`/`VEREDICTO` intocados, FAIL volta à prosa clara; medição em `references/scripts.md`.
- `dupla.py` — segundo juiz sobre o MESMO estado; `concordancia.md` por critério. Um juiz só bate "over
  80% agreement" com humanos e "favors itself" (https://arxiv.org/abs/2306.05685); júri de famílias
  distintas "outperforms a single large judge" (https://arxiv.org/abs/2404.18796). Discordância =
  critério ambíguo, não "juiz ruim". `dupla.py --balanco` soma os últimos 10 ciclos e sai 1 acima de 3
  (o segundo juiz aprovando o que o primeiro reprova) — aí a troca do juiz padrão vai ao dono (régua: decisão),
  porque juiz mais fraco que o executor já derrubou acerto de 91,4% para 82,8% (https://arxiv.org/abs/2607.21656).
- `custo_historico.py` — tabela por instância a partir de
  `~/.claude/ocombo-custo.log` (local, fora do canal): estamos ficando mais
  baratos ou não.
- `assets/rubricas/` — critérios binários por tipo (bot, site,
  script-agendado, receita-maquina, skill), nascidos das armadilhas desta
  casa; todo arquivo começa com C0 CONFORMIDADE (v6, Superpowers: "spec
  compliance, then code quality") e termina com REGRESSÃO. O juiz julga NA
  ORDEM e para se C0 reprovar (resto N/A; a rodada seguinte julga FAIL + N/A).
  Adaptar, não copiar cego. v12: `texto`, `pesquisa`, `desenho`, `acao`, cada critério [MEDIDO] ou [LEITURA].

## Papéis são agentes — quem pergunta, quem faz, quem julga (v10)

Cada papel é um subagente com contexto, ferramentas e modelo próprios, para que quem escreve a SOLUÇÃO
não seja quem perguntou nem quem julga — "Each subagent
runs in its own context window with a custom system prompt, specific tool access, and independent
permissions" (https://code.claude.com/docs/en/sub-agents). Arquivos em `assets/agentes/`, instalação
por `python scripts/instalar_agentes.py` (`--verificar` é portão), detalhe e limite honesto em
`references/papeis.md`.

- **`ocombo-grelha`** (lâmina 1) — `model: sonnet` (ordem do dono, 01/10/2026: Sonnet 5.5 nos subagentes) e
  sem `Edit`: quem pergunta não escreve código; entrega o `solucao.txt`.
- **`ocombo-executor`** (lâminas 3 e 4) — `model: inherit` (a sessão, Fable/Opus, é quem faz): TDD e portões;
  não toca veredicto nem `aprovado.sha256`.
- **`ocombo-juiz`** (lâmina 2) — `model: sonnet` e sem `Edit`/`Write`: quem julga não conserta; roda o `juiz.py`.
- **Maestro é a sessão principal** — roda a porta, delega, guarda o ledger e leva a régua ao dono. Papel
  nenhum abre subagente, e executor e juiz nunca saem na mesma delegação.

## Porta de entrada — a grelha não é obrigatória (v10)

`python scripts/porta.py --pedido "..." [--reparo|--novo] [--arquivos N] [--regua ...]` decide as
lâminas por FATO declarado e imprime as três linhas que entram no ESTADO (Porta, Lâminas, Papéis).
DISPENSA a grelha quando não há decisão a abrir: reparo pontual, escopo fechado, H1..Hn fechados,
critério de pronto claro. OBRIGA quando é peça nova, escopo largo (>= 5 arquivos), decisão em aberto ou
pedido sem critério de pronto — e quando toca a régua, aí `--forcar sem-grelha` sai 2: ordem não desliga
portão. Grelha pulada sem o motivo escrito no ESTADO é FAIL em C0.

## Juiz por diff — o juiz relê só o que mudou (v2)

Rodada 1 o juiz lê tudo; da rodada 2 em diante lê `delta.patch` e julga APENAS os critérios que estavam
FAIL mais o critério de REGRESSÃO. É o que a Anthropic recomenda para revisor — "A reviewer running in a
fresh subagent context sees only the diff and the criteria you give it"
(https://code.claude.com/docs/en/best-practices) — e o que o CodeRabbit faz por padrão. Mecânica de
`scripts/juiz.py` (testes puros em `scripts/test_juiz.py`, sem chamar `claude`):

- `prova.bat` na instância roda ANTES: exit ≠ 0 → AJUSTE sem juiz (0 tokens).
- snapshot `historico/solucao.rN.txt` → `delta.patch` (difflib) → prompt da
  rodada N cita os FAIL do `historico/veredicto.r(N-1).md`.
- cada rodada é um `claude -p` novo: contexto limpo, sem histórico da conversa.
- diff cru precisa do contexto do hunk ("expands each modified hunk to include
  the enclosing function", https://tianpan.co/blog/2026-05-05-llm-code-review-production-diff-pipeline):
  na SOLUÇÃO, descreva o que mudou e onde — o juiz abre o trecho, não a pasta.
  Medido na v2: rodada completa USD 0,82/200 s → rodada por diff USD 0,55/136 s.
- prefixo estável = cache barato (leitura a 0,1× do preço em Sonnet/Haiku, 0,05× no Opus 5.5, 0,025× no Fable,
  https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching):
  fixe modelo e ferramentas do juiz antes da esteira — "Switching models
  recomputes the entire request" (https://code.claude.com/docs/en/prompt-caching).

## Hooks — portões que custam zero tokens (v2)

Checagem mecânica não fica na memória do agente: vira hook, "deterministic control: certain actions
always happen rather than relying on the LLM to choose to run them"
(https://code.claude.com/docs/en/hooks-guide). Modelo pronto em `assets/hooks.exemplo.json` +
`assets/portao-hook.py`; o dono instala por projeto. Os quatro eventos que usamos (PostToolUse em
Edit|Write, Stop com `exit 2`, PreToolUse em `Bash(git commit*)`, hook que FILTRA a saída antes do
modelo ver), as armadilhas e as fontes: `references/hooks.md`. Hook não substitui juiz.

## Paralelismo — só o ruidoso e o desacoplado (v2)

Multiagente custa "about 15× more tokens than chats"
(https://www.anthropic.com/engineering/multi-agent-research-system). Subagente só para trabalho RUIDOSO
(pesquisa, log, varredura: volta resumo, nunca o dump); worktree só para partes DESACOPLADAS; nunca
paralelize código acoplado nem o TDD; um juiz por instância. Regras e fontes em `references/paralelismo.md`. v14: `scripts/ram.py` mede a RAM livre antes do portão/juízes (vagas; aperto = um por vez + `OCOMBO_SEM_MCP=1`); acelerar = contexto curto (`/compact`), effort e tier.

## Plano como fonte única — contexto limpo por lâmina (v2)

O `solucao.txt` da instância É o plano; a conversa não é. Rito:

- Seção ESTADO no topo (lâmina atual, rodada, feito, pendente, próximo passo,
  contexto herdado inviolável) — atualizada a cada lâmina, nunca reconstruída
  da memória. É o "structured note-taking" da Anthropic e o handoff de Pocock
  ("referenced by path or URL, never copied", https://www.aihero.dev/skills-handoff).
- Cada lâmina começa limpa: o papel (subagente) que lê só o ESTADO, ou `/clear` + "leia solucao.txt" —
  "start a fresh session to execute it. The new session has clean context"
  (https://code.claude.com/docs/en/best-practices).
- Spec Kit e Kiro separam spec/plan/tasks em três arquivos; aqui a instância faz isso com UM — não crie
  três. O que carrega em toda sessão tem de ser magro: skill sob demanda, pesquisa em `references/`.

## Gasto medido por rodada — custo.log (v2)

"ROI medido, não sentido" agora tem instrumento: `scripts/juiz.py` chama
`claude -p --output-format json` — "the response payload includes
`total_cost_usd` and a per-model cost breakdown"
(https://code.claude.com/docs/en/headless) — e grava em `custo.log` uma
linha por rodada: modelo, input, output, cache_read, cache_write, USD,
segundos, effort (v13). Sem usage no JSON = linha "sem usage" (nunca chute).

- `cache_read`/`cache_write` contam à parte do input
  (https://code.claude.com/docs/en/agent-sdk/cost-tracking); o USD é "client-side estimates, not
  authoritative billing data" — evidência de tendência, não fatura.
- Interativo: `/usage` antes de cada `/clear`, porque o total zera na sessão nova
  (https://code.claude.com/docs/en/commands). Histórico por sessão: `ccusage session --json`
  lê os JSONL de `~/.claude/projects/` (https://github.com/ryoppippi/ccusage).
- A ENTREGA anexa o `custo.log`; a memória do projeto registra o total. Tudo INTERNO: custo (USD, tokens) NUNCA vai ao dono em mensagem, pergunta, cupom ou página; só se ele perguntar (o dono, 29/09/2026: "pare de contar os custos, registre isto universalmente").

## Ferramentas de teste — o que roda ANTES do juiz

Linter `scripts/qualidade.py`, suíte, smoke `scripts/smoke_web.py`, tipos, hook de commit, smoke
pós-deploy e a armadilha do eslint: receita em `references/pacotes/codigo.md` (pacote de código). Ordem
fixa na lâmina `akita`, tudo com exit code, 0 tokens.

## Pacotes por natureza (v12) — o mesmo combo fora do código

- `iniciar.py --tipo texto|pesquisa|desenho|acao` abre a instância com a régua do tipo e a linha
  `Pacote       : <tipo> (ler references/pacotes/<tipo>.md)` no ESTADO; os 5 tipos de código (pacote
  `codigo`) saem byte a byte como antes. O dono não aprende palavra nova: o combo escolhe o tipo.
- Todo critério de qualidade é [MEDIDO] (comando + exit code) ou [LEITURA] (segundo leitor de outro
  tier citando a linha; sem citação = FAIL), com [LEITURA] em no máximo 1/3. Gosto aparece no fecho
  como "não provado por máquina", nunca como medida.
- Jev é ferramenta opcional de nota (mínimo combinado antes da rodada 1), nunca portão.
- Pedido misto: vale a natureza do que o dono recebe; código gerador leva também o pacote `codigo`.
- Fase 2 pendente (`porta.py --natureza`, `portao_texto.py`, `regressao_hash.py`): só depois de 1 ciclo
  real não-código APROVADO com a Fase 1. Gatilho e o que saiu do SKILL.md: `references/versoes.md`.

## Régua de escalada — quando chamar o dono (v5, 06/09/2026)

Decisão do dono em 06/09/2026: "quero fazer tudo deste terminal e ter IAs que revisem o trabalho e só
me chamem quando for algo mais sério". O dono não lê código; quem lê é o juiz. A régua é fechada e
curta — tudo fora dela o juiz aprova e o executor segue, sem pergunta na conversa:

| chamar o dono quando… | exemplo desta casa |
|---|---|
| **dinheiro** sai, entra ou se compromete | pagar, contratar plano, comprar licença |
| **produção** no ar muda | deploy na VPS, restart de serviço, DNS, nginx, tarefa agendada nova |
| **apagar** dado ou histórico | `rm`, drop, `git push --force`, reescrever backup |
| **terceiro** recebe algo em nome dele | mensagem, e-mail, PDF a grupo, post, publicação |
| **decisão** dele mudaria (H1..Hn do ESTADO) | reabrir escolha fechada, trocar ferramenta, mudar regra |

- Mecânica: o passo que cai na régua entra no ledger (`scripts/ledger.py escalar <instância> <tipo>
  "<o que precisa>"`) e a esteira PARA nele — o resto do ciclo continua. O "sim" do dono é registrado
  com a frase dele (`ledger.py sim`), nunca inferido. `ledger.py pendentes` sai 1 com escalada aberta:
  é portão (prova.bat ou hook) antes de qualquer lâmina de produção.
- Juiz e executor de tiers diferentes, sempre (a sessão Fable/Opus executa; julga o Sonnet 5.5, e o Gemini não entra
  no processo desde a v16, 26/10/2026); item que caiu na régua leva `dupla.py`
  (segundo juiz Opus) antes de chegar ao dono — o dono recebe a decisão já revisada duas vezes, não o rascunho.
- O dono vê sem ler código: `ledger.py resumo [dia]` imprime o cupom do dia (ciclos, rodadas,
  veredictos, USD, o que esperou o "sim"); o `juiz.py` grava cada veredicto no ledger sozinho, e o
  diário do dia puxa essa linha como fonte. Envio do cupom a grupo continua exigindo "sim" (H3).
- Rúbrica: todo tipo ganhou o critério de ESCALADA — nenhum passo da régua sem "sim" no ledger, e
  nenhum passo FORA da régua esperando humano.

## Destravar humanos POR DENTRO do produto

Quando um passo depende de gente (aprovação, assinatura, entrada de equipe), o combo NÃO agenda reunião:
desenha o gate como UM TOQUE dentro do produto (card com botão, lista de permissões, bloqueio
fail-closed) — o humano continua decidindo, mas sem sair do fluxo. Regra dupla do juiz: o
mecanismo nunca remove o humano da decisão (P1) e nunca abre mais do que o provado quando um arquivo
falha (fail-closed, P2).

## Sommelier de modelos — por papel e por TAREFA (v11, 20/09/2026)

Modelo por papel, não por fé; benchmark = o SEU caso de uso; ROI medido (`/usage`, `custo.log`), nunca
sentido; rúbrica sempre com critério de regressão; a responsabilidade é de quem assina. Quem OMITE `model`
num fan-out HERDA a sessão (20/09/2026: 88 agentes de transcrição em Fable até o dono parar a esteira).
**Antes de TODO fan-out: `python scripts/sommelier.py --plano "transcricao:44,conferencia:44" --workflow`**; as linhas `Sommelier:` e `Lancamento:` entram no ESTADO.

- **Esforço pelos dois caminhos:** a ferramenta Agent aceita `model` e `effort` (`low|medium|high|xhigh|max`; o fork
  ignora effort) e o Workflow aceita os dois em `agent(prompt, {model, effort})`. Nó ou papel com esforço escolhido
  leva o trecho `SOMMELIER` do `--workflow` ou o `effort` do Agent; a linha `Lancamento:` declara modelo e esforço de cada classe.
- **O Jev escolhe o modelo e a força** (o dono, 04/10/2026): `--plano`/`--tarefa` + `--descricao` perguntam ao Jev (`jev_escolha.py`); as travas abaixo valem por cima; sem Jev = regra fixa com o motivo na linha; `OCOMBO_JEV=off` desliga.
- **Regra fixa (sem Jev):** `varredura` haiku · `transcricao`, `pesquisa`, `redacao` sonnet · `conferencia` no tier que o autor NÃO usou
  (cross-model) · `julgamento` é do `modos.py` · `codigo` e `sintese` herdam a sessão. Classe fora da lista levanta erro.
- **Lote nunca no topo:** 3+ agentes da mesma classe jamais rodam em Fable, em modo nenhum (o 10
  também); decisão em lote desce para Opus. `--checar "transcricao:44=fable"` sai 2: é régua de
  DINHEIRO, só com o "sim" do dono no ledger.
- **Modo alto compra conferência e effort, nunca tier de lote.** Preço relativo ao Fable (tabela de 25/09/2026):
  Haiku 0,1× · Sonnet 5.5 0,2× · Opus 5.5 0,4× — o plano acima custa 30% do mesmo plano todo no topo. Tabela,
  os 41 testes (`scripts/test_sommelier.py`) e os limites em `references/sommelier.md`.

## Fechos obrigatórios

- Carimbo FINAL do juiz sobre a ENTREGA (não só sobre o desenho): anexe a seção ENTREGA ao
  solucao.txt com as evidências (exit codes, incidentes, custo.log, pendências) e rode o juiz de novo.
  "Rerun agendado não é exit code" — feche as medições antes de pedir o carimbo.
- **Fable 5.1 no máximo julga SEMPRE o resultado no fim** (o dono, 03/10/2026): `scripts/fecho_fable.py <instância>`
  depois do carimbo. ACEITO = ele escreve a mensagem `.441` (4 × 40 palavras, cérebro frito: verifiquei · outro
  agente reportou · não provado · espera o "sim"), entregue como está; REFAZER = rodadas só sobre os motivos +
  carimbo + Fable de novo, até 3 vezes (exit 3 = parada honesta ao dono). Cupom fora. Executor Fable: declare.
- Registre o ciclo na memória do projeto e a lição nova na constituição, com o CUSTO medido da
  rodada (tokens/modelo por papel) que o `custo.log` expõe.

## Armadilhas já pagas (29/08 a 06/09/2026)

Lista completa em `references/armadilhas.md` (as mais caras no topo).
- Mais caras: `ssh` sem `-n` no `while read` (portão falso-verde); segredo nunca literal no canal (SHA-256 local).
