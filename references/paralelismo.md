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
