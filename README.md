<h1 align="center">⚙️ O Combo · Claude Code skill</h1>

<p align="center">
  <strong>Grelha → juiz cross-model → TDD → produção, sem parar no meio.</strong><br>
  Uma esteira para entregar um sistema inteiro com o Claude Code, com um <em>segundo modelo</em> julgando cada rodada por diff, custo medido em dólar e uma régua curta que diz quando o humano precisa ser chamado.<br>
  <em>A Claude Code skill that chains plan-grilling, a cross-model judge that re-reads only the diff, real TDD and production gates — with per-round cost logging and an explicit escalation rule. Written in Brazilian Portuguese.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skill-blueviolet?style=for-the-badge" alt="Claude Code Skill">
  <img src="https://img.shields.io/badge/Idioma-pt--BR-009c3b?style=for-the-badge" alt="pt-BR">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License">
</p>

---

## 🤔 O que é isto

O Combo é uma **skill do [Claude Code](https://code.claude.com/docs/en/skills)** que descreve como trabalhar um projeto de ponta a ponta com o mínimo de idas e vindas ao dono e o mínimo de tokens. Ela nasceu em 29/08/2026, numa noite em que um bot foi ao ar por exatamente este caminho, e desde a v2 é julgada por ela mesma: cada versão tem fonte auditada em `references/`, portão em `prova.py` e testes puros em `scripts/test_*.py`.

A esteira tem quatro lâminas, sempre nesta ordem:

| # | lâmina | o que faz | ferramenta neste repo |
|---|---|---|---|
| 1 | **grelha** | a árvore de decisões vira um questionário numerado com a resposta recomendada em cada pergunta; decisão já fechada pelo dono nunca é reaberta | `scripts/decisoes.py` (grep nas memórias) |
| 2 | **juiz por diff** | o plano vira `solucao.txt` numa instância própria com rúbrica binária; um **modelo de outro tier** julga cada rodada lendo só o que mudou, com timeout, custo por rodada e carimbo SHA-256 do plano aprovado | `scripts/iniciar.py`, `rubrica.py`, `triagem.py`, `scripts/juiz.py`, `dupla.py` |
| 3 | **TDD** | só depois do APROVADO: vermelho antes do módulo, lógica pura separada da fiação, arquivos < 500 linhas, portão único | `scripts/qualidade.py` (ruff + eslint), `smoke_web.py` (Playwright), hooks |
| 4 | **produção** | deploy só por script com portões; sucesso = exit code e id, nunca opinião; incidente vira teste de regressão | `scripts/ledger.py` (régua de escalada) |

O texto da skill (`SKILL.md`, 300 linhas) é o que o modelo lê. Tudo que é pesquisa, medição e armadilha paga mora em `references/`, carregado sob demanda.

## 🧠 As ideias que valem a leitura

- **Juiz cross-model por diff.** Quem executa (Fable/Opus) nunca é quem julga (Sonnet por padrão). Rodada 1 o juiz lê tudo; da rodada 2 em diante lê `delta.patch` e julga só os critérios que estavam FAIL mais o critério de regressão. Medido: rodada completa USD 0,82 → rodada por diff USD 0,55.
- **Zero tokens antes do juiz.** `prova.bat` da instância, triagem determinística da forma, linter de correção e smoke de navegador rodam ANTES de qualquer chamada ao modelo. Vermelho ali é AJUSTE sem juiz.
- **Rúbrica criticada por um modelo barato** antes da rodada 1, porque quem escreve a régua é quem será julgado por ela.
- **Custo por rodada** em `custo.log` (modelo, tokens, cache, USD, segundos) e histórico entre projetos: ROI medido, não sentido.
- **Régua de escalada** fechada e curta: o dono é chamado por dinheiro, produção, apagar, terceiro ou decisão dele. O resto o juiz aprova. Cada escalada entra num ledger e a esteira para só naquele passo.
- **Dupla de juízes com balanço.** Um segundo juiz sobre o mesmo estado, concordância por critério, e um contador que avisa quando o juiz padrão está reprovando o que o outro aprova.

Cada afirmação acima tem fonte com trecho literal em `references/pesquisa-*.md` (documentação da Anthropic, arXiv 2306.05685, 2404.18796, 2605.30803, 2607.21656, CodeRabbit, Playwright, ruff, eslint).

## 🚀 Instalação

Requisitos: Python 3.10+, o [Claude Code](https://code.claude.com/docs/en/overview) instalado (`claude` no PATH) e, opcionalmente, `ruff` (`pip install ruff`), `eslint` e `@playwright/test` para as ferramentas de teste.

```bash
git clone https://github.com/Galgan1/ocombo.git ~/.claude/skills/ocombo
python ~/.claude/skills/ocombo/prova.py        # exit 0 = a skill está íntegra
```

Depois, em qualquer sessão do Claude Code:

```
/ocombo <o que você quer entregue>
```

Atualizar é `git pull` na mesma pasta.

## 🛠️ Como a esteira roda na prática

```bash
S=~/.claude/skills/ocombo/scripts
python $S/iniciar.py minha-instancia --tipo site       # instância + solucao.txt com a rúbrica do tipo
python $S/rubrica.py minha-instancia                   # Haiku critica a rúbrica (centavos)
python $S/juiz.py minha-instancia                      # prova.bat → triagem → juiz Sonnet por diff → custo.log
python $S/juiz.py --carimbo minha-instancia            # exit 0 = plano aprovado não mudou desde o carimbo
python $S/dupla.py minha-instancia                     # segundo juiz (Opus) + concordância por critério
python $S/qualidade.py <repo>                          # ruff F/E9 + eslint no-undef/no-unused-vars
python $S/smoke_web.py https://.../ --texto "Entrar"   # abre no Chromium headless, falha em erro de JS/5xx
python $S/ledger.py resumo                             # cupom do dia: ciclos, veredictos, USD, escaladas
```

Tipos de rúbrica prontos em `assets/rubricas/` (bot, site, script-agendado, receita-maquina, skill); hooks de zero tokens em `assets/hooks.exemplo.json` + `assets/portao-hook.py`. A referência de cada script, com exit codes, está em `references/scripts.md`.

## 🔗 As quatro skills que o Combo encadeia

O Combo é a esteira; ele cita quatro skills irmãs pelo nome. Este repositório traz **todos os scripts** que a esteira precisa (inclusive `scripts/loop_init.py`, que cria a instância do loop), então ele funciona sozinho. As irmãs são a doutrina que ele resume:

| skill | papel no combo | se você não a tem |
|---|---|---|
| `grilling` | interrogar o plano até a árvore de decisões ficar explícita | o questionário auto-respondido descrito em `SKILL.md` cumpre o papel |
| `loop-agente` | Planner → Executor → Verifier com rúbrica e teto de rodadas | `scripts/loop_init.py` + `juiz.py` são o loop |
| `akita` | disciplina de engenharia: TDD real, portão único, receita versionada | as regras estão resumidas na lâmina 3 |
| `producao-senior` | evidência = exit code, os enganos que já custaram caro, portões de publicação | as regras estão resumidas na lâmina 4 e em `references/armadilhas.md` |

## 🪟 Portabilidade

Desenvolvido e provado no Windows 11 (o portão da instância é `prova.bat`; o juiz chama `claude.cmd`). No Linux e macOS o juiz roda o `prova.sh` da instância quando existe, e a CI deste repo executa `prova.py` no Ubuntu e no Windows. O `iniciar.py` procura o instalador do loop em `OCOMBO_LOOP_INIT` e, sem a variável, usa o `scripts/loop_init.py` deste repo.

## 🔁 Como este repositório é publicado

A skill vive na máquina do autor; este repo é o espelho público gerado por `tools/publicar.py`, que copia a skill, normaliza LF e troca por um mapa local (fora do repo) os nomes de projetos e pessoas da casa. `tools/prova_repo.py` é o portão: roda a prova da skill e reprova se sobrar caminho de máquina, telefone, e-mail, CPF, token ou termo privado. É o que a CI roda.

## 📜 Licença

MIT — veja [LICENSE](LICENSE). Os trechos citados em `references/` pertencem às suas fontes e estão lá como citação, com URL.
