---
name: ocombo
description: >-
  O COMBO — a forma de trabalhar que colocou um bot de atendimento no ar em 29/08/2026, agora
  método padrão para entregar QUALQUER sistema de ponta a ponta com o mínimo de idas e vindas ao
  dono e o mínimo de tokens. Encadeia QUATRO skills numa esteira só: grilling (/grill-me vira
  questionário auto-respondido), loop-agente (juiz CROSS-MODEL por DIFF, custo medido, Sonnet 5
  padrão / Opus 5 no "extra"), akita (TDD, portão único, arquivos menor que 500, receita
  versionada) e producao-senior (evidência = exit code, portões de publicação). Tem régua de
  escalada própria — só chama o dono por dinheiro, produção, apagar, terceiro ou decisão dele.
  Use SEMPRE que o dono disser "/ocombo", "o combo", "usa o combo", "faz pelo sistema completo",
  "coloca no ar com o sistema", ou pedir um projeto entregue com revisão por juiz sem parar no
  meio — inclusive destravando gates humanos POR DENTRO do produto (botão no bot em vez de
  reunião). Histórico de versões (v2 a v8) no corpo, seção Versões.
---

# O COMBO — grelha → juiz → TDD → produção, sem parar no meio

Nasceu em 29/08/2026, na noite em que um bot de atendimento foi ao ar por este
exato encadeamento (7+ rodadas de juiz, 13+ achados, 2 incidentes que viraram teste),
sob a ordem "só volte quando estiver pronto". Da v2 em diante a skill é julgada por
ela mesma: cada versão tem fonte auditada em `references/` (v2 = `pesquisa-2026-09-05.md`,
v3 = `pesquisa-2026-09-05-v3.md`, v4 = `pesquisa-2026-09-06-v4.md`, v6 =
`pesquisa-2026-09-06-v6.md`), portão em `prova.py`, scripts em `references/scripts.md`;
v7 = espelho público github.com/Galgan1/ocombo (scripts.md, seção final).

## Versões

Changelog resumido; o detalhe de cada peça está na seção correspondente abaixo.

- **v2** (05/09/2026) — cinco economias provadas na fonte: juiz só sobre o diff, hooks
  como portões de zero tokens, paralelismo só do ruidoso ou desacoplado, plano como
  fonte única, custo.log por rodada. Ver "Juiz por diff", "Hooks", "Paralelismo",
  "Plano como fonte única" e "Gasto medido por rodada" abaixo.
- **v3** (05/09/2026) — as ferramentas: `iniciar.py` num comando, crítica da rúbrica
  por modelo barato, triagem determinística, dupla de juízes com concordância, timeout
  do juiz, histórico de gasto entre projetos, banco de rúbricas por tipo e decisões
  fechadas puxadas da memória. Ver "Ferramentas da esteira" abaixo.
- **v4** (06/09/2026) — ferramentas de teste que rodam ANTES do juiz: linter de
  correção (ruff F/E9 + eslint no-undef/no-unused-vars) em qualquer repo, smoke de
  navegador com Playwright para tudo que tem tela, hook de commit que barra o
  vermelho. Ver "Ferramentas de teste" abaixo.
- **v5** (06/09/2026) — régua de escalada: o dono só é chamado por dinheiro, produção,
  apagar, terceiro ou decisão dele; o resto o juiz aprova, com ledger, cupom do dia e
  critério de rúbrica. Ver "Régua de escalada" abaixo.
- **v6** (06/09/2026, depois da busca na comunidade) — três peças pequenas: carimbo
  preso ao SHA-256 do plano aprovado (claudex-loop), C0 CONFORMIDADE antes da
  qualidade com o juiz parando no primeiro bloco reprovado (Superpowers), balanço da
  dupla de juízes que mede se o Sonnet está sendo mais duro que o Opus (arXiv
  2607.21656).
- **v7** — espelho público github.com/Galgan1/ocombo.
- **v8** (07/09/2026) — crítica do juiz em modo caveman (regras da skill `caveman`
  embutidas no prompt de `juiz.py`, `OCOMBO_CAVEMAN=off|lite|full|ultra`, padrão
  full); `CRITERIO`/`VEREDICTO` intocados, FAIL volta à prosa clara. Ver `juiz.py`
  em "Ferramentas da esteira" abaixo.

## As quatro lâminas, na ordem

1. **`grilling` (/grill-me)** — mapeie a árvore de decisões e escreva o
   QUESTIONÁRIO: perguntas numeradas + a SUA resposta recomendada em cada
   uma. Quando o dono delegar ("responda com as suas sugestões" / "sem
   humano"), as respostas são suas — mas NUNCA reabra decisão que o dono já
   fechou: cite-a como contexto herdado inviolável na TAREFA. Rascunho do
   herdado: `scripts/decisoes.py <palavras>` (grep nas memórias).
2. **`loop-agente`** — o questionário vira `solucao.txt` numa INSTÂNCIA
   própria (`scripts/iniciar.py <pasta> --tipo T` faz tudo num comando), com
   RÚBRICA binária fixa no topo e a seção ESTADO (modelo em
   `assets/solucao.modelo.txt`). Antes da rodada 1, `scripts/rubrica.py`
   (Haiku) critica a rúbrica. O juiz é `python scripts/juiz.py <instância>
   [modelo]` — **cross-model sempre** (executor Fable/Opus → juiz do outro
   tier; padrão `claude-sonnet-5`, "extra" = `claude-opus-5` ou
   `scripts/dupla.py`); `emular_verificador.bat` é o reserva. Teto de
   rodadas: o que o dono fixar (padrão 5); estourou = parada honesta, entrega
   melhor versão + pendência declarada e PERGUNTA se vale rodada extra.
   Follow-up é cirúrgico: mexa SÓ no que reprovou. APROVADO grava
   `aprovado.sha256` do plano (v6): mudou o `solucao.txt` depois, o carimbo
   caducou — `juiz.py --carimbo <instância>` exit 0 é portão antes da lâmina 3.
3. **`akita`** — só depois do APROVADO: TDD de verdade (prove o VERMELHO
   antes do módulo), lógica pura separada da fiação, arquivos <500 linhas,
   portão único (`teste.js`/`prova.py`), constituição atualizada, um commit
   por mudança operacional.
4. **`producao-senior`** — deploy SÓ pelo script com portões; bateria de
   produção com critério novo para cada feature; `portao-publicacao.sh`
   exit 0 antes de publicar; sucesso = exit code e id, nunca opinião;
   incidente NUNCA se maquia — vira teste de regressão + linha no changelog,
   e critério vermelho transitório espera a janela em vez de ganhar exceção.

## Ferramentas da esteira (v3) — uma linha cada, detalhe em references/scripts.md

- `iniciar.py` — um comando abre a instância (loop_init + solucao.txt com a
  rúbrica do tipo + decisões herdadas + evidencias/ corpus/ prova.bat).
- `decisoes.py` — decisões fechadas puxadas da memória por grep (markdown +
  grep, sem RAG — Akita). Reabrir decisão do dono é o erro mais caro do combo.
- `rubrica.py` — modelo barato critica a régua ANTES do julgamento: fecha o
  ponto cego de "quem escreve a rúbrica é quem será julgado por ela". Fonte:
  "changing the rubric changes the response quality measurement induced by a
  fixed judge" e rúbrica vaga "can reward polished answers that invent facts"
  (https://arxiv.org/abs/2605.30803); a Anthropic pede critério "Empirical or
  specific" e "a different model to evaluate"
  (https://platform.claude.com/docs/en/test-and-evaluate/develop-tests).
- `triagem.py` — checagem determinística da forma antes do juiz (0 tokens):
  ESTADO, RUBRICA numerada com REGRESSÃO, SOLUÇÃO, caminhos citados existem.
  Ordem oficial: "1. Code-based grading: Fastest and most reliable … 3.
  LLM-based grading" (mesma URL); a cascata barata "caught roughly 60% of
  failures the judge would have caught"
  (https://futureagi.com/blog/how-i-built-deterministic-llm-evaluation-metrics-2026/).
  Gera `manifesto.txt` (caminho, bytes, sha256) — identificadores leves para
  o juiz abrir só o que a SOLUÇÃO cita.
- `juiz.py` — prova.bat → triagem → snapshot/delta/manifesto → juiz com
  timeout (900 s, 1 repetição; 2× = INDEFINIDO, nunca AJUSTE) → veredicto +
  custo.log + histórico global. Matar o `claude -p` por fora dá "exit code
  143 … records no result" (https://code.claude.com/docs/en/headless). v8 (07/09/2026): a crítica sai em modo caveman (regras da skill `caveman` embutidas no prompt; `OCOMBO_CAVEMAN=off|lite|full|ultra`, padrão full); `CRITERIO`/`VEREDICTO` intocados, FAIL volta à prosa clara; medição em `references/scripts.md`.
- `dupla.py` — segundo juiz sobre o MESMO estado; `concordancia.md` por
  critério. Um juiz só bate "over 80% agreement" com humanos e "favors itself"
  (https://arxiv.org/abs/2306.05685); júri de famílias distintas "outperforms a
  single large judge" e custa "seven to eight times less"
  (https://arxiv.org/abs/2404.18796). Discordância = critério ambíguo, não
  "juiz ruim". v6: grava no ledger quantas vezes o Opus aprovou o que o Sonnet
  reprovou; `dupla.py --balanco` soma os últimos 10 ciclos e sai 1 acima de 3
  — aí a troca do juiz padrão vai ao dono (régua: decisão). Motivo: no par
  Claude/Codex, juiz mais fraco que o executor DERRUBOU o acerto de 91,4% para
  82,8% (https://arxiv.org/abs/2607.21656); Fable→Sonnet são tiers da mesma
  família e a direção é a mesma — medir antes de confiar.
- `custo_historico.py` — tabela por instância a partir de
  `~/.claude/ocombo-custo.log` (local, fora do canal): estamos ficando mais
  baratos ou não.
- `assets/rubricas/` — critérios binários por tipo (bot, site,
  script-agendado, receita-maquina, skill), nascidos das armadilhas desta
  casa; todo arquivo começa com C0 CONFORMIDADE (v6, Superpowers: "spec
  compliance, then code quality") e termina com REGRESSÃO. O juiz julga NA
  ORDEM e para se C0 reprovar (resto N/A; a rodada seguinte julga FAIL + N/A).
  Adaptar, não copiar cego.

## Juiz por diff — o juiz relê só o que mudou (v2)

Rodada 1 o juiz lê tudo; da rodada 2 em diante lê `delta.patch` e julga
APENAS os critérios que estavam FAIL mais o critério de REGRESSÃO. É o que a
Anthropic recomenda para revisor: "A reviewer running in a fresh subagent
context sees only the diff and the criteria you give it"
(https://code.claude.com/docs/en/best-practices), e o que a indústria faz
por padrão (CodeRabbit: "incremental review of new changes only",
https://docs.coderabbit.ai/reference/review-commands). Mecânica de
`scripts/juiz.py` (testes puros em `scripts/test_juiz.py`, sem chamar `claude`):

- `prova.bat` na instância roda ANTES: exit ≠ 0 → AJUSTE sem juiz (0 tokens).
- snapshot `historico/solucao.rN.txt` → `delta.patch` (difflib) → prompt da
  rodada N cita os FAIL do `historico/veredicto.r(N-1).md`.
- cada rodada é um `claude -p` novo: contexto limpo, sem histórico da conversa.
- diff cru precisa do contexto do hunk ("expands each modified hunk to include
  the enclosing function", https://tianpan.co/blog/2026-05-05-llm-code-review-production-diff-pipeline):
  na SOLUÇÃO, descreva o que mudou e onde — o juiz abre o trecho, não a pasta.
  Medido na v2: rodada completa USD 0,82/200 s → rodada por diff USD 0,55/136 s.
- prefixo estável = cache barato (leitura a 0,1× do preço; Fable 0,025×,
  https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching):
  fixe modelo e ferramentas do juiz antes da esteira — "Switching models
  recomputes the entire request" (https://code.claude.com/docs/en/prompt-caching).

## Hooks — portões que custam zero tokens (v2)

Checagem mecânica não fica na memória do agente: vira hook, "deterministic
control: certain actions always happen rather than relying on the LLM to
choose to run them" (https://code.claude.com/docs/en/hooks-guide). Modelo
pronto em `assets/hooks.exemplo.json` + `assets/portao-hook.py`; o dono
instala por projeto (é config da máquina dele, a skill não grava settings).

- `PostToolUse` em `Edit|Write` roda o portão do projeto; vermelho cai no
  contexto na hora. A doc avisa: "the tool already ran" — realimenta, não desfaz.
- `Stop` bloqueia o fim com portão vermelho: `exit 2` + JSON
  `{"decision":"block","reason":...}`; `exit 1` "Claude treats it as a
  non-blocking error and stops anyway" (https://amitkoth.com/claude-code-stop-hooks/).
  Respeitar `stop_hook_active`; a doc corta após 8 bloqueios seguidos sem
  progresso (https://code.claude.com/docs/en/hooks-guide).
- Hooks disparam em `-p`: "a `-p` session runs the hooks in a project's
  `.claude/settings.json`" (https://code.claude.com/docs/en/headless); `--bare`
  desliga. Provado por `scripts/test_hook.py` e `scripts/prova_hook_vivo.py`.
- `PreToolUse` com `if: "Bash(git commit*)"` para suíte antes de commit;
  eventos disponíveis (SubagentStop, TaskCompleted, PreCompact…) em
  https://code.claude.com/docs/en/hooks.
- Hook também FILTRA antes de o modelo ver: "a hook can grep for ERROR and
  return only matching lines" (https://code.claude.com/docs/en/costs).
- Hook rápido, juiz completo: hooks "don't replace code review"
  (https://renedekkers.nl/posts/claude-code-hooks-automatic-testing/).

## Paralelismo — só o ruidoso e o desacoplado (v2)

Multiagente custa "about 15× more tokens than chats"
(https://www.anthropic.com/engineering/multi-agent-research-system). Subagente só para trabalho RUIDOSO
(pesquisa, log, varredura: volta resumo, nunca o dump); worktree só para partes DESACOPLADAS; nunca
paralelize código acoplado nem o TDD; um juiz por instância. Regras e fontes em `references/paralelismo.md`.

## Plano como fonte única — contexto limpo por lâmina (v2)

O `solucao.txt` da instância É o plano; a conversa não é. Rito:

- Seção ESTADO no topo (lâmina atual, rodada, feito, pendente, próximo passo,
  contexto herdado inviolável) — atualizada a cada lâmina, nunca reconstruída
  da memória. É o "structured note-taking" da Anthropic e o handoff de Pocock
  ("referenced by path or URL, never copied", https://www.aihero.dev/skills-handoff).
- Cada lâmina começa limpa: subagente que lê só o ESTADO, ou `/clear` +
  "leia solucao.txt". A doc é explícita: "start a fresh session to execute
  it. The new session has clean context" e "After two failed corrections,
  /clear and write a better initial prompt" (https://code.claude.com/docs/en/best-practices).
  Plan Mode com `showClearContextOnPlanAccept` faz isso num toque
  (https://code.claude.com/docs/en/permission-modes#analyze-before-you-edit-with-plan-mode).
- Spec Kit e Kiro separam spec/plan/tasks em arquivos ("code serves
  specifications", https://github.com/github/spec-kit/blob/main/spec-driven.md);
  aqui a instância cumpre o mesmo papel com um arquivo só — não crie três.
- O que carrega em toda sessão tem de ser magro: CLAUDE.md "under 200
  lines", skill "load on-demand" (https://code.claude.com/docs/en/costs).
  Por isso esta skill é curta e a pesquisa mora em `references/`.

## Gasto medido por rodada — custo.log (v2)

"ROI medido, não sentido" agora tem instrumento: `scripts/juiz.py` chama
`claude -p --output-format json` — "the response payload includes
`total_cost_usd` and a per-model cost breakdown"
(https://code.claude.com/docs/en/headless) — e grava em `custo.log` uma
linha por rodada: modelo, input, output, cache_read, cache_write, USD,
segundos. Sem usage no JSON = linha "sem usage" (nunca chute).

- `cache_read`/`cache_write` contam à parte do input
  (https://code.claude.com/docs/en/agent-sdk/cost-tracking); o USD é
  "client-side estimates, not authoritative billing data" — evidência de
  tendência, não fatura.
- Interativo: `/usage` (`/cost` é alias) antes de cada `/clear`, porque o
  total zera na sessão nova (https://code.claude.com/docs/en/commands,
  https://code.claude.com/docs/en/costs). Histórico por sessão: `ccusage session --json`
  lê os JSONL de `~/.claude/projects/` (https://github.com/ryoppippi/ccusage).
- Preço por 1M (input | cache read | output): Fable 5.1 USD 10 | 0,25 | 50;
  Opus 5 USD 5 | 0,50 | 25; Sonnet 5 USD 2 | 0,20 | 10; Haiku 4.5 USD 1 | 0,10 | 5
  (https://platform.claude.com/docs/en/about-claude/pricing). Juiz Sonnet
  custa 1/5 do executor Fable no input — o sommelier abaixo não é gosto.
- A ENTREGA anexa o `custo.log`; a memória do projeto registra o total.

## Ferramentas de teste — o que roda ANTES do juiz (v4, 06/09/2026)

A suíte prova o que alguém pensou em testar; as ferramentas abaixo pegam o que ninguém pensou.
Ordem fixa dentro da lâmina `akita`, todas com exit code anexado na instância, todas com custo zero
de tokens. Fontes e medições da estreia em `references/pesquisa-2026-09-06-v4.md`.

- **Linter = `scripts/qualidade.py <repo>`** — ruff `--select F,E9` nos `.py` (nome indefinido,
  import/variável sem uso, sintaxe; estilo NÃO entra) e eslint com `assets/eslint.config.base.mjs`
  nos `.js` (`no-undef`, `no-unused-vars`, regras de correção do recommended; lê `"type": "module"`
  do package.json; pula bundle minificado). É o teste anti-símbolo-órfão que a suíte não faz (o bot
  caiu 2 min em 29/08/2026 por dois símbolos que `node --check` e o teste puro não viram). Estreia
  em 06/09/2026: 4 repos, achado real em 3 — e na própria skill (F401, F823 no `smoke_web.py` recém-
  escrito). Exit 1 = AJUSTE sem juiz. Regras de rúbrica: bot, site, script-agendado, skill ganharam
  o critério C7 de lint; o `prova.py` desta skill roda o ruff em si mesmo.
- **Suíte** (`pytest`/`vitest`, vermelho→verde) — exit 0 anexado; flake se repete, não se afrouxa.
- **Smoke de navegador = `scripts/smoke_web.py <url> --texto <esperado>`** para tudo que tem tela
  (site, painel interno, app interno): copia `assets/playwright/` para a pasta que tem `@playwright/test`
  (`OCOMBO_NODE_TOOLS` ou o repo) e abre a URL no Chromium headless; falha com erro de JS no
  console, request 5xx ou texto ausente. `curl -I` prova que o servidor responde; Playwright prova que
  a página abre — "Playwright Test is an end-to-end test framework for modern web apps"
  (https://playwright.dev/docs/intro). Instalar uma vez: `npm i -D @playwright/test && npx playwright
  install chromium`. A config fixa um projeto (chromium), 1 worker, 0 retries.
- **Tipos e cobertura** só quando o repo já tem (`tsc --noEmit`, `mypy`, `--coverage`): não se instala
  ferramenta nova no meio de um ciclo; entra como decisão da grelha do próximo.
- **Hook `PreToolUse` em `Bash(git commit*)`** (`assets/hooks.exemplo.json`) roda `qualidade.py` e o
  portão do projeto antes de cada commit: o commit vermelho nem nasce, 0 tokens.
- **Smoke pós-deploy** (`portao-publicacao.sh`, `curl -I`, id retornado) segue na lâmina `producao-senior`.
- Duas armadilhas medidas na estreia: config do eslint que faz `import '@eslint/js'` resolve relativo ao
  ARQUIVO da config e quebra quando o eslint mora em outra pasta (a config da skill não importa nada);
  `require('@playwright/test')` idem — por isso o `smoke_web.py` copia spec e config para perto do
  `node_modules` (https://eslint.org/docs/latest/use/configure/configuration-files,
  https://docs.astral.sh/ruff/rules/).

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
- Juiz e executor de tiers diferentes, sempre (Fable/Opus executa, Sonnet julga); item que caiu na
  régua leva `dupla.py` (segundo juiz Opus) antes de chegar ao dono — o dono recebe a decisão já
  revisada duas vezes, não o rascunho.
- O dono vê sem ler código: `ledger.py resumo [dia]` imprime o cupom do dia (ciclos, rodadas,
  veredictos, USD, o que esperou o "sim"); o `juiz.py` grava cada veredicto no ledger sozinho, e o
  diário do dia puxa essa linha como fonte. Envio do cupom a grupo continua exigindo "sim" (H3).
- Rúbrica: todo tipo ganhou o critério de ESCALADA — nenhum passo da régua sem "sim" no ledger, e
  nenhum passo FORA da régua esperando humano.

## Destravar humanos POR DENTRO do produto

Quando um passo depende de gente (aprovação, assinatura, entrada de equipe),
o combo NÃO agenda reunião: desenha o gate como UM TOQUE dentro do produto
(card com botão no bot, allowlist viva, overlay de assinaturas fail-closed) —
o humano continua decidindo, mas sem sair do fluxo. Regra dupla do juiz:
o mecanismo nunca remove o humano da decisão (P1) e nunca abre mais do que o
provado quando um arquivo falha (fail-closed, P2).

## Sommelier de modelos — custo por papel (30/08/2026)

Modelo por papel, não por fé; benchmark = o SEU caso de uso; ROI medido (`/usage`, `custo.log`), nunca
sentido; rúbrica sempre com critério de regressão; a responsabilidade é de quem assina. Texto completo
(Mano Deyvin auditado + rodada Odisséia) em `references/sommelier.md`.

## Fechos obrigatórios

- Carimbo FINAL do juiz sobre a ENTREGA (não só sobre o desenho): anexe a
  seção ENTREGA ao solucao.txt com as evidências (exit codes, incidentes,
  custo.log, o que ficou pendente) e rode o juiz de novo. "Rerun agendado não
  é exit code" — feche as medições antes de pedir o carimbo.
- **Mensagem final ao dono na notação `.441`** (decisão do dono em 06/09/2026): quatro parágrafos de
  40 palavras, registro cérebro frito (zero jargão, uma analogia do dia a dia, frases curtas). Dentro
  deles: o que EU verifiquei · o que outro agente reportou · o que não deu para provar · o que ficou
  esperando o "sim". O cupom do dia (`ledger.py resumo`) NÃO entra na mensagem — o ledger continua sendo
  gravado e fica disponível para o diário e para quando ele pedir. O detalhe técnico mora na instância.
- **PDF ao grupo de relatórios do WhatsApp NÃO é fecho do combo.** Esse envio (nota ≥ 9 → PDF + minuta
  por um script de envio) é EXCLUSIVO da minuta jurídica (skill de documento jurídico,
  referência própria). Correção do dono em 05/09/2026, quando o ciclo da notação v3 quase mandou
  um PDF ao grupo. Em qualquer outro ciclo o relatório fica na instância e na conversa; grupo só com "sim".
- Registre o ciclo na memória do projeto e a lição nova na constituição, com o CUSTO medido da
  rodada (tokens/modelo por papel) que o `custo.log` expõe.

## Armadilhas já pagas (29/08 a 06/09/2026)

Lista completa, com data e antídoto, em `references/armadilhas.md`. As que mais custaram:

- Portão verde com lista CURTA demais é suspeito: `ssh` sem `-n` dentro de `while read` engolia a lista e o deploy
  de uma integração fiscal ficou falso-verde de 30/08 a 02/09. Confira a CONTAGEM do portão com `git status`.
- Prova "verificado" só vale com artefato na pasta do juiz, gerado DEPOIS do último conserto, com o nome que a
  rúbrica cita; a seção ENTREGA é julgada como fato (`stat`, exit code), nunca como narrativa.
- Extração de módulo deixa SÍMBOLO ÓRFÃO que `node --check` e teste puro não pegam (bot caiu 2 min): a suíte
  executa a fiação e o `qualidade.py` (v4) roda antes do juiz.
- Segredo nunca vira literal em portão que viaja pelo canal (SHA-256 em arquivo local); `$` seguido de dígito no
  SKILL.md vira argumento; heredoc do Bash quebra com texto longo em pt-BR (grave por Write, confira com `file`).
- Resumo de terceiro (vídeo, blog) não entra na esteira sem auditoria na fonte; o juiz `claude -p` roda em sandbox
  e só lê a instância — copie o corpus e prove a cópia por SHA-256.
