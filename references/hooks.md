# Hooks — portões que custam zero tokens (v2)

Saiu do SKILL.md em 09/09/2026 para abrir espaço à seção Modos, sem perder uma linha: o corpo da
skill fica magro e o detalhe carrega sob demanda ("Move detailed reference material to separate
files", https://code.claude.com/docs/en/skills). O modelo pronto continua em
`assets/hooks.exemplo.json` + `assets/portao-hook.py`.

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
