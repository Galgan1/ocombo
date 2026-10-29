# Pacote codigo

O caminho de codigo de sempre: sistema, bot, site, script agendado, receita de maquina, skill. As 5 reguas
antigas (`assets/rubricas/bot.txt`, `site.txt`, `script-agendado.txt`, `receita-maquina.txt`, `skill.txt`)
pertencem a este pacote, e o `iniciar.py` desses 5 tipos NAO grava linha `Pacote` no ESTADO: o solucao.txt
sai byte a byte como antes da v12. A lamina 3 e a `akita` e a 4 e a `producao-senior`, sem troca nenhuma.

O corpo abaixo saiu palavra por palavra da secao "## Ferramentas de teste" do SKILL.md na v12 (29/09/2026);
o titulo ficou la, com um ponteiro para ca.

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
  install chromium`.
- **Tipos e cobertura** só quando o repo já tem (`tsc --noEmit`, `mypy`, `--coverage`): ferramenta nova
  no meio do ciclo, não; entra como decisão da grelha do próximo.
- **Hook `PreToolUse` em `Bash(git commit*)`** (`assets/hooks.exemplo.json`) roda `qualidade.py` e o portão do projeto antes de cada commit: o commit vermelho nem nasce, 0 tokens.
- **Smoke pós-deploy** (`portao-publicacao.sh`, `curl -I`, id retornado) segue na lâmina `producao-senior`.
- Armadilha medida na estreia: config do eslint e `require('@playwright/test')` resolvem relativo ao
  ARQUIVO e quebram com a ferramenta em outra pasta — por isso o `smoke_web.py` copia spec e config para
  perto do `node_modules` (https://eslint.org/docs/latest/use/configure/configuration-files).
