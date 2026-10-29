# Sommelier de modelos (movido do SKILL.md em 06/09/2026, v5; texto original)

Destilado dos vídeos de terceiros (transcrições auditadas) + uma rodada interna de 20/09:

- **Modelo por papel, não por fé.** Executor caro onde há densidade
  (arquitetura, backend, refatoração); juiz/tarefa simples em tier barato.
  Já provado aqui: juiz Sonnet acha o que o executor Fable não acha.
  Apostar tudo num modelo único = refém de um provedor.
- **Benchmark = o SEU caso de uso.** Benchmark público (ou da própria
  vendedora do modelo) não decide nada; antes de promover modelo novo a um
  papel da esteira, rode UM ciclo do combo com ele e compare medições.
- **ROI medido, não sentido.** Custo é evidência como exit code: tokens de
  input/output da sessão (`/usage`, `custo.log`), nunca "pareceu barato".
- **Rúbrica sempre tem critério de regressão**: "o que já passava continua
  passando" — acrescentar feature sem destruir o pronto é o que separa
  modelo utilizável de brinquedo.
- **A responsabilidade é de quem assina.** "A m* é sua, não da Anthropic":
  revisão final humana (ou do dono da esteira) antes do carimbo, sempre.

## Sommelier por TAREFA (v11, 20/09/2026) — `scripts/sommelier.py`

**O incidente que pariu a peca.** Em 20/09/2026 o maestro abriu um Workflow de 44 lotes x 2 estagios
(transcrever por visao um documento escaneado de 300+ paginas + segundo leitor) e NAO passou `model` em
nenhum `agent()`. A regra da ferramenta e clara — quem omite `model` herda o modelo da sessao — e a
sessao era Fable: 88 agentes de trabalho mecanico no tier mais caro da casa. O dono parou a esteira:
"chamar fable 40x e insanidade". O sommelier por papel (acima) nao cobria isso: ele escolhe o modelo
da grelha, do executor e do juiz, nao o de cada tarefa de um fan-out.

**As cinco regras** (cada uma com teste em `scripts/test_sommelier.py`, 41 testes; os da CLI rodam com `OCOMBO_JEV=off`):

| # | regra | teste |
|---|---|---|
| R1 | a CLASSE da tarefa decide o tier — nunca a sessao, nunca o habito | `test_o_caso_que_pariu_a_regra` |
| R2 | LOTE NUNCA NO TOPO: 3+ agentes da mesma classe jamais rodam no tier de topo, em nenhuma classe, nenhum modo (o 10 tambem) e nenhuma sessao; classe de decisao em lote desce um tier | `test_lote_nunca_no_topo` (varre 8 classes x 12 modos x 4 sessoes x 4 tamanhos) |
| R3 | quem confere e de tier DIFERENTE de quem fez (cross-model), acima quando o autor e barato | `test_conferente_e_cross_model` |
| R4 | modo alto compra CONFERENCIA e EFFORT, nunca tier de lote | `test_modo_alto_compra_effort_nao_tier` |
| R5 | topo em lote a pedido e regua de DINHEIRO: `--checar` sai 2 e a esteira para no ledger | `test_checar_sai_2_no_lote_de_topo` |

**A tabela de classes** (lista FECHADA — classe fora dela levanta erro em vez de herdar em silencio):

| classe | tier | effort | o que e |
|---|---|---|---|
| `varredura` | haiku | low | listar, grep, classificar arquivo, ler log, triagem de pasta |
| `transcricao` | sonnet | medium | imagem/audio/PDF escaneado -> texto fiel; extracao estruturada |
| `pesquisa` | sonnet | medium | web, documentacao, leitura de fonte que volta resumo + fontes |
| `redacao` | sonnet | medium | capitulo, resumo de livro, documentacao, mensagem |
| `conferencia` | sai do autor: haiku->sonnet, sonnet->opus, opus->sonnet, fable->sonnet | high (xhigh do modo 7 em diante; low no F1) | segundo leitor cetico do trabalho de OUTRO agente |
| `julgamento` | o juiz do modo (`modos.py`) | o `juiz_effort` do modo | juiz de rubrica — o sommelier nao disputa com o `modos.py` |
| `codigo` | herda a sessao; em lote desce para opus | — | implementacao com TDD (acoplado fica na sessao principal) |
| `sintese` | herda a sessao; em lote desce para opus | high | arquitetura, decisao dificil, sintese final de um fan-out |

**Precos** (saiu do SKILL.md na v11; USD por 1M, input | cache read | output; tabela de 25/09/2026, fonte em
`references/pesquisa-2026-10-02-v13.md`): Fable 5.1 USD 10 | 0,25 | 50; **Opus 5.5 USD 4 | 0,20 | 20**;
Sonnet 5.5 USD 2 | 0,20 | 10; Haiku 4.5 USD 1 | 0,10 | 5
(https://platform.claude.com/docs/en/about-claude/pricing). Juiz Sonnet custa 1/5 do executor Fable no
input — o sommelier nao e gosto. Como a saida custa 5x a entrada em TODOS os tiers, a razao entre
tiers nao depende da mistura input/output: Haiku 0,1x · Sonnet 0,2x · **Opus 0,4x** do Fable (era 0,5x com o
Opus 5). O teste `test_razao_entrada_saida_igual_em_todo_tier` quebra no dia em que um preco mudar essa premissa.
**Geracao anterior nao e economia (v13):** Opus 5 USD 5 | 25, Opus 4.8 USD 5 | 25 e Sonnet 4.6 USD 3 | 15 custam
igual ou MAIS que Opus 5.5 e Sonnet 5.5 — quem quer gastar menos troca de TIER ou de EFFORT, nunca de geracao.

**O caso do dia, refeito:** `--plano "transcricao:44,conferencia:44"` = 44 x 0,2 + 44 x 0,4 sobre 88 =
**30%** do mesmo plano todo em Fable (era 35% com o Opus 5). Com `--tokens entrada,saida` (volume MEDIDO por
agente) a CLI da o USD de tabela; sem volume medido nao ha USD — a casa nao chuta.

**Como o maestro usa.** Antes de todo fan-out: roda `--plano ... --workflow`, cola as linhas `Sommelier:` e
`Lancamento:` no ESTADO e passa em cada chamada o `alias` E o `effort` devolvidos —
`agent(prompt, {model: 'sonnet', effort: 'medium'})` no Workflow — ou o `modelo` (id completo) em
`claude -p --model --effort`. A ferramenta Agent (`model: "sonnet"`) só para classe de effort padrão (secao abaixo).
Pedido explicito do dono vence a tabela (como o explicito vence o modo), mas lote no topo continua
sendo dinheiro: `ledger.py escalar <instancia> dinheiro "..."` e espera o "sim".

**Limites honestos.** (1) O custo relativo ignora cache, cujo desconto varia por modelo (leitura Fable
0,025x, Opus 5.5 0,05x, Sonnet 5.5 e Haiku 0,1x do preco de entrada). (2) A tabela de classes e juizo desta casa, nao benchmark: o sommelier
por papel ja avisa que "benchmark = o SEU caso de uso" — classe nova entra com um ciclo medido, nao por
fe. (3) O script RECOMENDA e RECUSA; quem monta a chamada ainda e o maestro. O que impede o esquecimento
e a rubrica (criterio SOMMELIER em todos os tipos) e a linha no frontmatter da skill, que carrega em
toda sessao. (4) Transcricao por visao de simbolo miudo (simbolo miudo, numero de serie) em Sonnet ainda nao foi
medida contra gabarito nesta casa: por isso a conferencia em Opus vem junto, e nao depois.

## Esforço só pelo Workflow (04/10/2026) — `sommelier.py --workflow`

**A lacuna.** A ferramenta Agent aceita `model` mas NÃO aceita `effort`; só o `agent()` do Workflow aceita
(`opts.effort`: low, medium, high, xhigh, max; omitido = herda o effort da sessão). No ciclo de 04/10/2026 quase
todos os nós foram lançados pela ferramenta Agent e rodaram sem o esforço que o sommelier (e o Jev, por
`jev_escolha.py`) tinha escolhido: o modelo certo com a força errada.

**A regra.** Nó do grafo ou papel cuja linha Sommelier traz effort sai por Workflow `agent()` com `model` E
`effort` dela. A ferramenta Agent só quando o effort da classe é o padrão (`-` na tabela: hoje `codigo` sem Jev e o `julgamento` dos modos 0 e 1)
ou o tier é Haiku, e isso fica declarado no ESTADO pela linha `Lancamento:`.

**Haiku sem effort (medido 04/10/2026):** `claude -p --model claude-haiku-4-5-20251001 --effort low "diga ok"` saiu 0 com "ok" (a CLI aceita); o `agent()` do Workflow não dá para medir de fora; o catálogo da metajev diz que o Haiku 4.5 não aceita effort (a API dá erro), então `opcoes_workflow` omite o effort no Haiku (efeito nulo) e `lancar_por` devolve `agent`.

**`--autor TIER`** diz o autor da conferência que ABRE o plano (`--tarefa conferencia` ou `--plano`/`--checar "conferencia:N,..."`); fora disso é erro de uso (exit 1). Até 04/10/2026 era descartado em silêncio no `--plano`/`--checar` (achado do revisor).

**A saída pronta.** `python scripts/sommelier.py --plano "transcricao:44,conferencia:44" --workflow` imprime, além
da tabela e da linha `Sommelier:`:

```
Lancamento: Workflow agent() model+effort: transcricao, conferencia
// Workflow: cada agent() leva model E effort (a ferramenta Agent NAO aceita effort)
const SOMMELIER = {
  "transcricao": {"model": "sonnet", "effort": "medium"},
  "conferencia": {"model": "opus", "effort": "high"}
}
// uso: agent(prompt, {...SOMMELIER["transcricao"], label: "..."})
```

Classe repetida no plano vira `classe_2`; classe de effort padrão sai só com `model` e cai na parte
`ferramenta Agent (effort padrao)` da linha `Lancamento:`. O objeto é JSON válido (o teste o lê com `json.loads`).

**A trava** (`scripts/test_sommelier.py`, classe `Workflow`, 9 testes):
`test_opcoes_trazem_effort_sempre_que_a_classe_tem` varre 8 classes x 12 modos x 4 sessões x 2 tamanhos e falha
se uma escolha com effort sair sem effort no `agent()` ou marcada para a ferramenta Agent; os outros cobrem o
effort do Jev, o trecho JS, classe repetida, a linha `Lancamento:` e a CLI (`--plano`/`--tarefa` com `--workflow`,
e a saída antiga sem ele).

**Limite honesto.** O script recomenda; quem monta a chamada ainda é o maestro. O `--workflow` só tira a
desculpa ("não tinha o effort à mão"); a rúbrica e a linha `Lancamento:` no ESTADO é que mostram ao juiz se o
nó foi lançado pelo caminho certo.
