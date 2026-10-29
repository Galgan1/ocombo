# Os MODOS do combo — 0 a 10, e o F1 (v9, 09/09/2026)

Um botão só. O número diz **quanto o combo investe acima do piso**, não o que ele deixa de checar.
Fonte de cada afirmação de terceiro: `references/pesquisa-2026-09-09-v9.md`. Código: `scripts/modos.py`
(tabela pura) e `scripts/test_modos.py` (29 testes). Ferramenta: `python scripts/modos.py` lista tudo.

## A regra que nenhum modo quebra

O piso é igual do 0 ao 10 e no F1 — `modos.PORTOES`, provado por teste em todos os perfis:

1. `prova.bat` da instância (exit ≠ 0 = AJUSTE sem juiz, 0 tokens);
2. triagem determinística da forma (0 tokens);
3. linter de correção (`qualidade.py`) antes do juiz (0 tokens);
4. régua de escalada: dinheiro, produção, apagar, terceiro, decisão do dono;
5. carimbo `aprovado.sha256` preso ao plano aprovado.

Modo alto não é permissão para pular etapa; é permissão para **gastar mais**. Modo baixo não afrouxa
portão; ele só não paga por rodada extra, dupla de juízes ou fan-out.

## Como escolher

- O dono diz o número (`/ocombo 7`, "modo 3", "manda de opala", "fórmula 1"). **Sem número, é 0.** v13: a dose
  colada (`--modo 3+`, `3+2`, `7-`) sobe ou desce degraus a partir do que ele disse; f1 não tem dose.
- Na instância: `python scripts/iniciar.py <pasta> --modo 7|f1` grava a linha no ESTADO.
- No ambiente: `OCOMBO_MODO=7` vale para o ciclo inteiro (o `juiz.py` lê sozinho).
- **Precedência:** argumento explícito (`juiz.py <pasta> claude-opus-5-5 --timeout 120 --effort high`) > modo > padrão.
- Regra de bolso: **0 a 3** trabalho de rotina; **4 a 6** coisa que outra pessoa vai usar; **7 a 9**
  dinheiro, produção ou dado de terceiro no meio; **10** quando errar custa mais caro que gastar;
  **F1** quando o relógio é o problema (janela curta, alguém esperando, incidente em curso).

## A escala (cada degrau ACRESCENTA ao anterior)

| # | apelido | juiz | effort do juiz | executor | teto | dupla | pesquisa | paralelo | timeout | custo rel. |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | padrão | Sonnet 5.5 | — | — | 5 | não | 0 | 2 | 900 s | 10 |
| 1 | conferido | Sonnet 5.5 | — | — | 5 | não | 0 | 2 | 900 s | 12 |
| 2 | atento | Sonnet 5.5 | high | — | 5 | não | 0 | 2 | 900 s | 15 |
| 3 | teimoso | Sonnet 5.5 | high | — | 7 | não | 0 | 2 | 900 s | 20 |
| 4 | lido | Sonnet 5.5 | high | — | 7 | não | 1 | 3 | 900 s | 26 |
| 5 | revisado | Sonnet 5.5 | high | — | 7 | fecho | 1 | 3 | 900 s | 34 |
| 6 | forte | Sonnet 5.5 | high | high | 7 | fecho | 1 | 3 | 900 s | 45 |
| 7 | desconfiado | Sonnet 5.5 | high | high | 9 | régua | 2 | 4 | 900 s | 60 |
| 8 | obcecado | Sonnet 5.5 | medium | high | 9 | régua | 2 | 4 | 1200 s | 78 |
| 9 | esquadrão | Sonnet 5.5 | medium | high | 9 | régua | 3 | 4 | 1200 s | 100 |
| 10 | **opala** | Sonnet 5.5 | medium | high | 9 | régua | 4 | 4 | 1800 s | 140 |
| f1 | **fórmula 1** | Sonnet 5.5 | low | — | 3 | não | 1 | 16 | 300 s | 55 |

`dupla` = régua: o segundo juiz (`dupla.py`) entra só no passo que cai na régua de escalada (dinheiro, produção,
apagar, terceiro, decisão do dono). Consolidado pelo dono em 29/10/2026,
depois do diagnóstico um diagnóstico interno de 29/10/2026: juiz em xhigh/max era 22% das rodadas e 70% do
tempo de juiz; a dupla concordava com o primeiro juiz em 2 de cada 3 vezes; nenhum perfil passa de 4 agentes por leva.

O que entra em cada degrau, em uma linha:

- **1 conferido** — carimbo da ENTREGA obrigatório: o juiz relê o que foi entregue, não só o desenho.
- **2 atento** — juiz em `--effort high`.
- **3 teimoso** — teto de 7 rodadas: insiste em vez de entregar com pendência.
- **4 lido** — 1 subagente de pesquisa auditada antes da grelha (fonte, não memória).
- **5 revisado** — `dupla.py` no fecho: segundo juiz sobre o mesmo estado, concordância por critério.
- **6 forte** — executor em `/effort high` (o juiz segue Sonnet 5.5 em todos os modos desde a v16).
- **7 desconfiado** — dupla nos passos da régua, teto 9.
- **8 obcecado** — timeout do juiz sobe para 1200 s (desde 29/10/2026 juiz `medium` e executor `high`: effort alto
  comprava espera, não certeza).
- **9 esquadrão** — fan-out de verificação adversarial (workflow `size medium`, em levas de 4 agentes).
- **10 opala** — pesquisa 4, timeout 1800 s, fan-out `size medium` em levas de 4, dupla nos passos da régua; juiz
  `medium` e executor `high`. Continua o mais caro da escala pelo volume de rodadas, pesquisa e fan-out, não pelo effort.

## F1 — velocidade e alta performance

O F1 **não é o modo 11**. O 10 queima para ganhar **certeza**; o F1 queima para ganhar **tempo**:

- tudo que é desacoplado sai em paralelo (até 16 agentes, o teto do runtime);
- `CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS=0` — sem a espera de até 5 s que faz os irmãos do fan-out
  reaproveitarem o cache do primeiro. Paga-se em `cache_write` e recebe-se tempo de volta;
- teto de 3 rodadas, juiz Sonnet em `--effort low`, timeout de 300 s: a rodada que não fecha vira parada
  honesta com pendência declarada, não uma quarta tentativa;
- sem dupla e sem crítica prévia da rúbrica (são passos seriais: custam relógio);
- **os cinco portões continuam iguais.** O que cai é a espera, nunca a prova.

**Pit stop (o turbo).** `modos.turbo(perfil)` liga o fast mode do Opus, "making the model up to 2.5x faster
at a higher cost per token". Ele **exige o "sim" do dono**, porque "fast mode is available via usage credits
only and not included in the subscription rate limits" — é dinheiro saindo fora da assinatura, régua v5.
Em `-p` o fast mode só entra por `claude -p --settings '{"fastMode": true}'`, e não existe em Sonnet nem
Haiku: por isso `turbo()` recusa qualquer perfil que não declare `turbo_disponivel`.

## Armadilhas medidas neste ciclo (09/09/2026)

- **`--effort` inválido não falha: avisa e roda.** `claude --effort banana -p` imprime
  `Warning: Unknown --effort value 'banana' — ignoring it` e executa mesmo assim (exit 0; a chamada de teste
  custou USD 0,47 em cache write do Opus 1M). Portão que avisa e deixa passar é o pior tipo: `modos.py`
  valida contra a lista fechada **antes** de montar a linha, e `argumentos_claude` levanta em vez de mandar.
- **A lista da doc não é a lista do binário.** A doc oferece `ultracode` em `/effort`; a build 2.1.263
  responde `Valid values: low, medium, high, xhigh, max`. Prova de máquina vence documentação: `ultracode`
  ficou como ajuste do executor, nunca como flag do juiz.
- **Apelido não é chave.** A primeira versão de `ambiente()` exportava `OCOMBO_MODO=conferido`, que
  `normalizar()` rejeita: o modo 1 não voltava. O teste de ida e volta (`ambiente` → `normalizar`) pegou.
- **Modo fora da escala não pode criar instância.** `iniciar.py --modo 11` recusa e **não** cria a pasta —
  mesma classe do `--help` que virou instância em 08/09/2026.

## v13 (02/10/2026) — a geração atual, a dose e a escada

**Ids.** Juiz dos modos 0–5 e F1: `claude-sonnet-5-5`; dos modos 6–10: `claude-opus-5-5` (eram Sonnet 5 e Opus 5).
Os dois rodaram pelo `juiz.py` em 01/10/2026 antes de virarem padrão (custo.log). Fonte dos preços e a medição:
`references/pesquisa-2026-10-02-v13.md`.

| modelo | id | USD in / out por 1M | observação |
|---|---|---|---|
| Fable 5.1 | `claude-fable-5-1` | 10 / 50 | topo; só a sessão, nunca lote (R2) |
| Opus 5.5 | `claude-opus-5-5` | 4 / 20 | **mais barato que o Opus 5 (5 / 25) e que o Opus 4.8 (5 / 25)** |
| Sonnet 5.5 | `claude-sonnet-5-5` | 2 / 10 | mesmo preço do Sonnet 5; Sonnet 4.6 custava 3 / 15 |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | 1 / 5 | crítica de rúbrica e varredura |

Regra que nasce aqui: **geração anterior não é economia**. Quem quer gastar menos muda de TIER (coluna juiz) ou de
EFFORT (coluna effort), nunca de geração. A coluna "custo rel." da tabela acima continua sendo juízo relativo entre
degraus, não conta de tabela.

**Dose colada ao modo.** `iniciar.py --modo 3+` abre a instância no 4; `3+2` no 5; `7-` no 6 (`modos.interpretar` →
`modos.ajustar`, preso em 0..10). `f1+` levanta: o F1 é outro eixo. `formula-1` continua sendo o F1 (apelido com hífen
não é dose).

**Escada.** `iniciar.py --escada` grava `escada: sim` na linha `Modo deste ciclo` do ESTADO (o plano é a fonte; a
variável `OCOMBO_ESCADA=1` vale como atalho). A cada rodada o `juiz.py` conta os `historico/veredicto.rN.md` que
terminaram em AJUSTE e sobe esse número de degraus a partir do modo de partida (`modos.escalar`): no máximo 3
acima, nunca sozinha ao 10 nem ao F1, e o piso (`modos.PORTOES`) não muda em degrau nenhum (teste
`test_escada_nao_mexe_no_piso`). Rodada aprovada de primeira não gasta nada acima do modo pedido. Por que subir
modo (effort e juiz) e não trocar o executor por tier menor: executor Sonnet obriga juiz Opus (cross-model) e o juiz
é a rodada cara do ciclo (medido: 0,58 USD/rodada no Sonnet 5 contra 0,05 da crítica de rúbrica).

**Effort explícito.** `juiz.py <pasta> [modelo] [--timeout s] [--effort e]`: explícito > modo > nenhum (a CLI
decide). A linha do `custo.log` ganha `effort=e` quando houver; `custo_historico.py --modelos` agrupa por modelo ×
papel × effort — é a bancada para refazer o sweep de effort do Sonnet 5.5 (a doc manda começar em `medium` para
trabalho agentic) antes de mexer no perfil 0, que continua sem `--effort`.
