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
