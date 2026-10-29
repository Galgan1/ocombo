# Versões do O COMBO — changelog

Saiu do SKILL.md em 09/09/2026 para o corpo ficar dentro do limite de 300 linhas do `prova.py` (corpo magro, detalhe em references/). Cada item aponta a seção do SKILL.md que o descreve.

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
- **v9** (09/09/2026) — os MODOS: um botao de 0 a 10 (0 = o padrao de sempre, 10 = "opala queimador de
  tokens") mais o perfil lateral **F1**, que troca token por TEMPO em vez de por certeza. Tabela pura em
  `scripts/modos.py` com 29 testes; `OCOMBO_MODO`, `iniciar.py --modo` e o `juiz.py` lendo o perfil
  sozinho (explicito vence o modo). Regra que nasce com a versao: **nenhum modo desliga portao** —
  prova, triagem, linter, regua de escalada e carimbo sao iguais do 0 ao 10 e no F1. Detalhe em
  `references/modos.md`, fontes em `references/pesquisa-2026-09-09-v9.md`.
- **v10** (10/09/2026) — os PAPEIS viram subagentes (`assets/agentes/*.md`, instalados por
  `scripts/instalar_agentes.py`): a grelha nao edita codigo, o juiz nao tem ferramenta de escrita e
  roda em modelo de outro tier, o executor nao toca veredicto nem carimbo — separacao por MECANISMO,
  nao por boa vontade. E a grelha deixou de ser obrigatoria: `scripts/porta.py` decide as laminas por
  fato declarado e escreve o motivo no ESTADO, mas recusa dispensar a grelha em pedido que toca a
  regua de escalada. Enxugadas no SKILL.md para caber no portao de 300 linhas (nenhuma REGRA saiu; o
  que saiu foi citacao ja auditada em `references/`): rubrica.py, triagem.py, dupla.py, smoke,
  armadilha do eslint, plano como fonte unica, /usage, fechos e custo. Ver "Papeis sao agentes" e
  "Porta de entrada" no SKILL.md, detalhe em `references/papeis.md`.
- **v11** (20/09/2026) — o SOMMELIER POR TAREFA: `scripts/sommelier.py` escolhe modelo e effort por
  classe de tarefa de um fan-out e RECUSA (exit 2) lote no tier de topo. Nasceu de incidente: 88
  agentes de transcricao em Fable porque o maestro omitiu `model` e o agente herdou a sessao; o dono
  parou a esteira ("chamar fable 40x e insanidade"). 30 testes em `scripts/test_sommelier.py`, criterio
  SOMMELIER em todas as rubricas, gatilho novo no frontmatter. Ver "Sommelier de modelos" no SKILL.md e
  `references/sommelier.md`. **O que saiu do SKILL.md para caber no portao de 300 linhas (C6 — nenhuma
  REGRA saiu):** (a) o item "Preco por 1M" de "Gasto medido por rodada" mudou inteiro para
  `references/sommelier.md`; (b) em "Juiz por diff" saiu a citacao literal do CodeRabbit ("incremental
  review of new changes only") com a URL, auditada em `references/pesquisa-2026-09-05.md`; (c) em
  "Plano como fonte unica" sairam as citacoes do Spec Kit ("code serves specifications") e da doc de
  custos ("load on-demand") com as URLs, auditadas na mesma pesquisa; (d) na armadilha do eslint saiu
  a URL das regras do ruff, auditada em `references/pesquisa-2026-09-06-v4.md`; (e) `rubrica.py`,
  `triagem.py` e `dupla.py` so tiveram as linhas re-quebradas (mesmo texto, mesmas URLs). A referencia
  "Texto completo (vídeos de terceiros auditados)" virou a mencao a `references/sommelier.md`
  no fim da secao nova.

- **v11.1 (28/09/2026)** — conserto do parser de veredicto (`scripts/juiz.py` `veredicto()`): o fallback que aprovava por `\bAPROVADO\b` solto saiu; sem linha canonica, FAIL de criterio ou AJUSTE = AJUSTE, e APROVADO em prosa = INDEFINIDO. Teste de regressao `test_aprovado_solto_em_prosa_nunca_aprova` (17 testes em `test_juiz.py`). Nasceu de carimbo falso real no ciclo um ciclo de 28/09/2026 (armadilhas.md, 28/09). `prova.py` da skill: 0 falhas.

- **v12 (29/09/2026)** — PACOTES POR NATUREZA (Fase 1; ciclo `ocombo-v12-uso-geral-2026-09-29`): o mesmo
  combo passa a servir oficialmente para texto, pesquisa, desenho e acao, sem mudar nada no caminho de
  codigo. `scripts/iniciar.py --tipo texto|pesquisa|desenho|acao` (TIPOS com 9 tipos, padrao continua
  `skill`, tipo invalido continua exit 2) cola a regua nova e, pela funcao pura `aplicar_pacote`, grava
  `Pacote       : <tipo> (ler references/pacotes/<tipo>.md)` depois da linha Papeis e reescreve
  `Lamina atual`; os 5 tipos antigos saem byte a byte como antes (15 golden conferidos). Reguas novas em
  `assets/rubricas/{texto,pesquisa,desenho,acao}.txt` (C0, ESCALADA e SOMMELIER com o texto das antigas;
  todo criterio de qualidade [MEDIDO] ou [LEITURA], [LEITURA] no maximo 1/3; Jev so como nota opcional).
  Pacotes em `references/pacotes/{codigo,texto,pesquisa,desenho,acao}.md`. Executor ganhou o passo 0
  (le o pacote), a grelha ganhou 1 linha, o `prova.py` ganhou 9 arquivos e 1 secao (nada saiu), o
  `test_v3.py` ganhou 12 testes (nenhuma linha antiga mexida). Nomes das laminas (`akita`,
  `producao-senior`) e `MAX_LINHAS_SKILL = 300` intactos; SKILL.md ficou com 293 linhas, entao a secao
  "Destravar humanos POR DENTRO do produto" NAO precisou sair.
  **O que saiu do SKILL.md, linha a linha, e para onde foi (C6 — nenhuma REGRA saiu):**
  (a) description, linha "Entrega QUALQUER sistema de ponta a ponta numa esteira só, com o mínimo de idas
  e vindas ao dono:" -> reescrita na mesma description como "Entrega QUALQUER trabalho (sistema, texto,
  pesquisa, desenho, acao) de ponta a ponta numa esteira só," + "com o mínimo de idas e vindas ao dono:",
  e a description ganhou a linha "Fronteira: mensagem avulsa é da skill `editor`; ciclo com juiz é do
  combo." (sem gatilho novo);
  (b) introducao, linha "portão em `prova.py`, scripts em `references/scripts.md`, changelog v2–v11 em
  `references/versoes.md`." -> a mesma linha com "v2–v12";
  (c) item `assets/rubricas/`, linha "Adaptar, não copiar cego." -> a mesma linha seguida de "v12:
  `texto`, `pesquisa`, `desenho`, `acao`, cada critério [MEDIDO] ou [LEITURA].";
  (d) o CORPO inteiro de "## Ferramentas de teste — o que roda ANTES do juiz (v4, 06/09/2026)", da linha
  "A suíte prova o que alguém pensou em testar..." ate "perto do `node_modules`
  (https://eslint.org/docs/latest/use/configure/configuration-files)." -> palavra por palavra em
  `references/pacotes/codigo.md`, secao de mesmo titulo. No SKILL.md ficaram o titulo (o SECOES do
  `prova.py` exige) e um ponteiro de 3 linhas. As duas URLs que sairam (playwright.dev/docs/intro e a do
  eslint) continuam auditadas em `references/pesquisa-2026-09-06-v4.md`.
  **Fase 2 pendente, com gatilho:** `porta.py --natureza` (4a linha so com a flag), `portao_texto.py`,
  `regressao_hash.py` e `test_pacotes.py` so entram depois de 1 ciclo real nao-codigo APROVADO pelo juiz
  usando a Fase 1 (tipo texto, pesquisa, desenho ou acao aberto pelo `iniciar.py`). Plano em
  `grelha.md` da instancia do ciclo, secao 2, passos 11 a 14.
  **Correcao dos conferentes (mesmo dia, antes da publicacao):** reguas aplicadas de cabeca a instancias
  reais nao eram julgaveis em dois pontos. (1) texto C2: "no mesmo item" nao dizia o que e item; um post
  com 8 itens numerados e rodape unico de fontes nao tinha como passar nem falhar por maquina. Agora
  item = paragrafo ou item numerado, e a fonte vale na linha do item ou num rodape com mapa numerado em
  corpus/ que o script cruza item a item (rodape sem mapa = FAIL). (2) acao C1/C5 pressupunham tela;
  acao por API, IMAP ou script aceita o log de texto do antes e do depois como captura, e C5 fica N/A
  declarado. De brinde, texto C1, desenho C2 e acao C2 exigem o vermelho anterior ao verde, conferido
  por comando. 3 testes novos em `test_v3.py` (vermelho antes da mudanca). Ficaram registrados sem
  mudanca: desenho nasce no teto de [LEITURA] (2 de 6, 3 x 2 = 6), sem folga para outro criterio de
  gosto; e o C0 comum a todas as reguas so detecta papel trocado lendo o ESTADO, pendencia para uma
  revisao de `skill.txt` que mude as 9 reguas juntas.

- **v13 (02/10/2026)** — A GERACAO ATUAL, A DOSE E A ESCADA (pedido do dono: "deixar as skills afiadas...
  considerando as IAs disponiveis"; revisao profunda sem instancia do combo, provada por `prova.py` 0 falhas).
  (a) **Ids e precos:** juiz padrao `claude-sonnet-5-5`, "extra"/dupla `claude-opus-5-5`, em `modos.py`
  (JUIZES_PERMITIDOS e os 12 perfis), `juiz.py`, `sommelier.py` (IDS; PRECO do Opus 4 | 20), `loop_init.py`,
  `assets/solucao.modelo.txt` e as referencias vivas; ambos os ids ja tinham rodado pelo `juiz.py` em 01/10/2026
  (custo.log: 2 rodadas Sonnet 5.5, 2 rodadas + 1 dupla Opus 5.5). Razao Opus/Fable cai de 0,5x para 0,4x e o
  caso do dia do sommelier de 35% para 30%. Regra nova em `sommelier.md`: geracao anterior (Opus 5, Opus 4.8,
  Sonnet 4.6) custa igual ou MAIS — economia e por tier ou effort, nunca por geracao. Portao novo no `prova.py`:
  nenhum id fora de ATUAIS em SKILL.md, scripts, assets e nas 4 referencias vivas (historia fica fora).
  (b) **Dose colada ao modo:** `iniciar.py --modo 3+ | 3+2 | 7-` (`modos.interpretar` -> `modos.ajustar`;
  f1 nao tem dose; apelido com hifen nao e dose).
  (c) **Escada pelo plano:** `iniciar.py --escada` grava `escada: sim` na linha do modo; `juiz.escada_ativa`
  le o plano ou `OCOMBO_ESCADA=1`; `modos.escalar` sobe 1 degrau por rodada AJUSTE (conta
  `historico/veredicto.rN.md`), ate 3 acima da partida, nunca sozinha ao 10 nem ao f1; `modos.PORTOES` iguais.
  (d) **Effort explicito no juiz:** `juiz.py <pasta> [modelo] [--timeout s] [--effort e]`
  (`resolver_effort`: explicito > modo > None) e a linha do custo.log ganha `effort=` quando houver (parser
  antigo continua lendo). (e) **Bancada de medicao:** `custo_historico.py --modelos` = media por modelo x papel
  x effort (USD/rodada, s/rodada, turnos, USD/turno, s/turno) — a resposta a "o modelo menor resolve igual?"
  passa a ser medida, nao palpite; qualidade continua no ledger. Medido em 02/10 sobre o log da casa: Sonnet 5.5
  fez 3,6 s/turno contra 8,8 s/turno do Sonnet 5 (n=2 x 426; amostra curta, direcao clara).
  (f) **Papeis:** `ocombo-grelha` passa a `model: sonnet` (ordem do dono em 01/10/2026, "utilize sonnet 5.5
  nos subagentes"); `ocombo-executor` fica `inherit` de proposito — trocar o executor por Sonnet obrigaria o juiz
  a subir para Opus e o juiz e a rodada cara. Instalados por `instalar_agentes.py` (--verificar 0).
  (g) **Uma fonte para o loop:** `scripts/loop_init.py` passa a ser copia byte a byte do da skill `loop-agente`
  (que ganhou `scripts/`, testes e `prova.py` proprios; v2 dela); o `prova.py` dos dois acusa divergencia.
  Pontes `executar.bat` e `emular_verificador.bat` aceitam `effort` como 2o argumento; `verificar.bat` julga em
  Sonnet 5.5. (h) **SKILL.md:** description 13 -> 11 linhas sem perder gatilho (menos tokens em toda sessao);
  corpo em 299 linhas; nenhuma REGRA saiu. Testes: test_modos +2, test_juiz +3, test_v3 +1; 123 verdes.
  Fontes e medicoes: `references/pesquisa-2026-10-02-v13.md`.
- **v14 (04/10/2026) — regra da RAM livre + acelerar:** pedido do dono ("registre no ocombo a regra da RAM livre
  e as estratégias para fazer as funções mais rapidamente como o compact"). `scripts/ram.py` (vagas pela RAM
  livre, linha do ESTADO), `OCOMBO_SEM_MCP=1` no `juiz.argumentos_claude` (+ `assets/mcp-vazio.json`; sem a
  variável, byte a byte), `references/paralelismo.md` ganhou "RAM livre manda no paralelo" e "Acelerar o
  raciocínio". Nasceu da vistoria de um projeto grande (portão morto 2x com 1,2 GB livres). test_ram +8.

## v14.1 (04/10/2026) — o Jev escolhe o modelo e a força
Ordem do dono: "Insira isto em ocombo o jev escolhe o modelo e a força". `scripts/jev_escolha.py` pergunta ao Jev
(choice de tier + score de effort, uma chamada por classe, pela ponte da skill jev); `sommelier.py --plano/--tarefa`
aplica a escolha e mantém por cima R2 (lote nunca no topo), R3 (conferente de outro tier), R4 (F1 compra tempo) e o
juiz de tier diferente da sessão. Sem Jev = regra fixa com o motivo. `OCOMBO_JEV=off` desliga. 9 testes novos
(`test_jev_escolha.py`, transporte dublê). Medido: plano real pesquisa/conferencia/sintese -> sonnet/opus/sonnet.

- **v14.2 (16/10/2026) — `qualidade.py` lê o "type" do package.json mais próximo:** defeito: o sourceType vinha só do package.json da raiz passada (`repo_esm`), e a raiz de um site, sem "type", acusou 85 Parsing error falsos em `app/client/**`, que declara "type": "module"; conserto: `esm_por_arquivo` sobe da pasta de cada .js até a raiz e o primeiro package.json que declara "type" decide, `agrupar_por_esm` manda ao eslint um grupo com `OCOMBO_ESLINT_MODULE=1` e outro com `=0`, e o relatório mostra `esm=1`, `esm=0` ou `esm=1:N/0:M`; sem "type" no caminho, tudo como antes; test_qualidade +4 (`TestEsmAninhado`, um deles fim a fim com o eslint real); origem: um ciclo de revisão de site, 16/10/2026 (critério C4).

- **v16 (26/10/2026) — o Gemini sai do processo:** ordem do dono, literal: "esqueça gemini. registre isto no processo."
  Motivo medido na r1 de um ciclo de 26/10/2026 (13:14): rodada INDEFINIDA, com o argon sem cota ("esgotado") e o
  flash vazio porque a leitura de arquivo foi auto-negada em headless. `modos.py`: juiz `claude-sonnet-5-5` nos 12 perfis
  (f1 com effort low), `JUIZES_PERMITIDOS` sem ids `agy:`. `juiz.py`: `MODELO_PADRAO = 'claude-sonnet-5-5'`; juiz agy vindo
  do modo ou do padrão vira Sonnet sempre; o backend agy fica só para id `agy:` explícito na linha de comando.
  SKILL.md, os agentes executor e juiz e `references/scripts.md` sem o Gemini como padrão. Testes: `test_v16_gemini_fora_do_processo`
  (novo), `test_juiz_claude_por_ambiente` e `test_julgamento_obedece_ao_modo` (atualizados): vermelho às 13:19:47 (3 falhas),
  verde às 13:20:20 (123 testes). `references/armadilhas.md` voltou a LF (estava em CRLF desde 25/10 00:34, o único FAIL
  da prova antes desta versão; conteúdo igual).
- **v15.1 (23/10/2026, fecho do Fable) — segredo nunca fica ao alcance do juiz:** defeito: a cópia só-leitura de `~/.claude.json`
  (chave de API em texto puro) feita na r3, antes da regra "arquivo solto na home", ficou 3 h em `historico/leitura/`, dentro
  do `--add-dir` do juiz do Google (conteúdo não lido, medido no sqlite do CLI; nome visto). Conserto com teste vermelho antes:
  `copias_de_leitura` purga `historico/leitura/` a cada rodada e recusa conteúdo com VALOR de segredo (`_RE_SEGREDO`: `sk_`, `sk-`,
  `AIza`, `gh?_`, `AKIA`, `xox?-`, PRIVATE KEY, json chave=valor); `segredos_na_instancia()` é pré-voo do `chamar_agy`: achou valor
  com cara de chave na instância = INDEFINIDO `segredo`, juiz não chamado. Palavra solta (`api_key` em prosa) não conta. test_juiz +2 (46).
- **v15 (23/10/2026) — o Antigravity CLI oficial (`agy`) é o juiz:** ordem do dono ("reduza o antigravity ao nosso juiz"). `modos.py`:
  `juiz='agy:gemini-4-argon-high'` em todos os perfis (f1 `-low`), ids `agy:*` em `JUIZES_PERMITIDOS`. `juiz.py`: backend por prefixo
  `agy:` (`chamar_agy`): fila de cota `gemini-4-argon → gemini-3.8-flash → claude-sonnet-5-5` com o mesmo sufixo (o agy recusa
  `--effort` junto do sufixo), cache "esgotado até" em `%LOCALAPPDATA%\ocombo\agy-cota.json`, `--add-dir` = raiz git de cada
  caminho citado na SOLUÇÃO (nunca home, Documents/.claude/.gemini inteiros, dados do app, `.secrets`), cópia só-leitura em
  `historico/leitura/` do arquivo citado fora das raízes, veredicto pelo campo `response` (o juiz não grava), tripwire da pasta da
  instância, INDEFINIDO por cota/permissão/timeout/violação (nunca AJUSTE, nunca cai calado no `claude -p`), `custo.log` em tokens
  com `usd=n/d`. `OCOMBO_JUIZ_CLAUDE=1` e a linha `^Dados ... pessoais$` do ESTADO (dados de cliente) voltam ao `claude-sonnet-5-5`.
  `sommelier.py`: classe `julgamento` com juiz `agy:*` = alias `agy` (não é subagente). 18 testes novos em `test_juiz.py`.
  Medido na 1ª instância real (antigravity-juiz): r1 triagem, r2/r3 INDEFINIDO por `view_file` auto-negado (daí as cópias),
  r4 prova vermelha (o agy omite chaves no padrão ao regravar o `settings.json`), r5 APROVADO em 432 s pelo flash.
- **v14.3 (17/10/2026) — critério novo no meio do ciclo também é julgado:** defeito: na rodada por diff, o `juiz.py` e o `dupla.py` mandavam ao juiz só o FAIL e o N/A do veredicto anterior. Um critério que entrou na RUBRICA depois (emenda do dono) nunca era julgado; num ciclo de video de 17/10/2026, o C7b e o C13b ficaram de fora da rodada 2. Conserto: `juiz.criterios_da_rubrica` lê os ids da seção RUBRICA; `juiz.pendentes_com_novos` soma aos pendentes os critérios que o veredicto anterior nunca julgou; o `juiz.py` e o `dupla.py` usam essa lista. Sem veredicto anterior, nada muda (rodada inteira). test_juiz +3 (`TestCriterioNovo`), vermelho às 15:03:24 e verde às 15:03:55; `prova.py` com 0 falha. Ajuste das 18:15 (a dupla Opus da rodada 3 mostrou o caso): 'nunca julgado' olha o HISTÓRICO inteiro (`juiz.historico_de_veredictos`), não só o último veredicto, porque na rodada por diff o juiz pode imprimir só o que julgou; test_juiz +1 (vermelho 18:15:10, verde 18:15:27).
