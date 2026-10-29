# Paralelismo (movido do SKILL.md em 06/09/2026, v5; texto original com as fontes)

Multiagente custa "about 15× more tokens than chats"
(https://www.anthropic.com/engineering/multi-agent-research-system); a
parcimônia A05 do `loop-agente` continua valendo. O que compensa:

- **Subagente para trabalho RUIDOSO** (pesquisa na web, leitura de logs,
  varredura de pasta): "returns only a condensed, distilled summary"
  (https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
  A conversa principal recebe conclusão + fontes, nunca o dump.
- **Worktree/instância para partes DESACOPLADAS** (N livros, N máquinas,
  N estações): `claude --worktree` ou `isolation: worktree`
  (https://code.claude.com/docs/en/worktrees); porta, banco e servidor de
  dev por worktree — "Worktrees isolate files but not runtime resources"
  (https://www.matthewswong.com/en/blog/claude-code-parallel-agents-git-worktrees/).
- **Nunca paralelize código acoplado nem o TDD iterativo**: fica na sessão
  principal quando "Multiple phases share significant context"
  (https://code.claude.com/docs/en/sub-agents). Juiz é um só por instância;
  "unreviewed parallel output is a liability" — não abra mais trabalhadores
  do que o juiz consegue julgar.
- Loop autônomo tipo Ralph ("while :; do cat PROMPT.md | claude-code; done",
  https://ghuntley.com/ralph/) só em greenfield e com portão como parada.
- **O modelo de cada agente sai do sommelier (v11, 20/09/2026)**: fan-out sem `model` herda a sessao e
  poe trabalho mecanico no tier de topo. `python scripts/sommelier.py --plano "..."` antes de abrir;
  lote nunca no topo. Regras e tabela em `references/sommelier.md`.

## RAM livre manda no paralelo (v14, 04/10/2026)

Medido numa máquina (16 GB, um pente): cada `claude -p` = ~330 MB + ~400 MB dos MCPs herdados
(dois MCPs); sessão interativa parada = 350-530 MB; Claude Desktop = ~530 MB; sessão de fundo
(`claude --bg`) volta sozinha quando o Claude Code se atualiza. Com 1,2 GB livres o portão grande da vistoria
de um projeto grande morreu 2x por memória; com 3,8 GB livres cabem 3 vagas.

- **Antes do portão e de cada fan-out de juízes:** `python scripts/ram.py`; a linha entra no ESTADO.
  vagas 1 = critérios um por vez (`--so=cN`) e juiz/dupla/fecho em fila; vagas >= 2 = pode rodar critérios
  independentes e dupla em paralelo até o número de vagas (o teto do juiz continua valendo).
- **Aperto (< 3 GB):** `OCOMBO_SEM_MCP=1` antes do `juiz.py`/`dupla.py`/`fecho_fable.py` — o juiz lê arquivo e
  roda prova; MCP não serve a ele.
- **Comando morto por falta de memória não é falha do comando:** registre na evidência e rode de novo sozinho;
  comando de fundo morto por memória só volta com o pedido do dono.
- **Liberar memória é do dono:** fechar sessão parada, Claude Desktop ou `claude stop <id>` de sessão de fundo
  só com o pedido dele; o combo mede e diz quanto sai, não fecha.

## Acelerar o raciocínio (v14) — RAM não acelera o modelo

A velocidade de cada resposta é da API, não da máquina; mais subagentes não aceleram o raciocínio, só
repartem trabalho desacoplado. O que acelera, na ordem de preferência:

1. **Contexto curto:** `/compact` entre lâminas longas e `/clear` + "leia solucao.txt" na troca de lâmina
   (o plano é a fonte única); cada resposta relê o contexto inteiro.
2. **Effort pela tarefa:** trabalho mecânico (transcrição, varredura, conferência de forma) em effort baixo;
   `--effort` só na lista fechada (`modos.validar_effort`).
3. **Tier pela classe:** o sommelier põe varredura em Haiku e transcrição/pesquisa/juiz em Sonnet — mais
   rápidos que o topo.
4. **Portão barato antes do caro:** prova.bat e triagem (0 tokens) antes do juiz; juiz por diff da rodada 2 em diante.
5. **`/fast`:** acelera o Opus, mas sai de crédito extra — só com o "sim" do dono no ledger (régua de dinheiro, v5).

