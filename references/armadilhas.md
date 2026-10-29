# Armadilhas já pagas — lista completa (29/08 a 06/09/2026)

## As que mais custaram (estavam no SKILL.md até 09/09/2026)

- Portão verde com lista CURTA demais é suspeito: `ssh` sem `-n` dentro de `while read` engolia a lista e o deploy
  de uma integração ficou falso-verde de 30/08 a 02/09. Confira a CONTAGEM do portão com `git status`.
- Prova "verificado" só vale com artefato na pasta do juiz, gerado DEPOIS do último conserto, com o nome que a
  rúbrica cita; a seção ENTREGA é julgada como fato (`stat`, exit code), nunca como narrativa.
- Extração de módulo deixa SÍMBOLO ÓRFÃO que `node --check` e teste puro não pegam (bot caiu 2 min): a suíte
  executa a fiação e o `qualidade.py` (v4) roda antes do juiz.
- Segredo nunca vira literal em portão que viaja pelo canal (SHA-256 em arquivo local); `$` seguido de dígito no
  SKILL.md vira argumento; heredoc do Bash quebra com texto longo em pt-BR (grave por Write, confira com `file`).
- Resumo de terceiro (vídeo, blog) não entra na esteira sem auditoria na fonte; o juiz `claude -p` roda em sandbox
  e só lê a instância — copie o corpus e prove a cópia por SHA-256.


Movida do SKILL.md em 06/09/2026 (v4) para manter o corpo da skill magro; o SKILL.md guarda o ponteiro e as mais caras. Nada foi apagado: cada item abaixo é o texto original.

- Portão verde com lista CURTA demais é suspeito (consertos de uma integração, 02/09/2026): o `--checar` do deploy
  listou 1 divergência quando havia 9 arquivos mudados e 5 novos — `ssh` sem `-n` dentro de `while read`
  engolia o resto da lista e o laço parava calado. Consertado, revelou 2 hotfixes vivos só na VPS que um
  deploy teria apagado. Antídoto: confira se a CONTAGEM do portão bate com a que você sabe (git
  status/diff --stat); `ssh` em laço sempre com `-n`.
- Prova "verificado" só vale com artefato na pasta do juiz (mesma rodada): alegar `node --check ok`, "ADR
  escrito" ou "medido no código" sem anexar saída/diff/trecho é AJUSTE certo — o juiz só lê a instância.
  Anexe `node_check_out.txt`, `docs.patch` e o trecho de código que sustenta cada "medido".
- Extração de módulo deixa SÍMBOLO ÓRFÃO que `node --check` e teste puro não pegam — o bot caiu 2 min em
  produção. Antídoto: a suíte EXECUTA os caminhos de fiação (não só os puros) e tem teste anti-símbolo-órfão.
- Dar ao juiz uma instância SEM o corpus de conferência = FAIL de lastro por culpa do executor. Copie para a
  instância tudo que a rúbrica manda conferir — o `claude -p` do juiz roda em sandbox e NÃO lê fora da pasta
  (ele mesmo declarou em 05/09/2026); prove "cópia fiel" por SHA-256 dos dois lados.
- `emular_verificador.bat` precisa de caminho absoluto no Git Bash (`cmd //c "C:\\...\\emular_verificador.bat <modelo>"`).
- O juiz barato acha coisa que você não acha: 13 achados legítimos em 13 reprovações — leia o veredicto
  inteiro antes de discordar.
- A seção ENTREGA é julgada como fato, não como narrativa (auditoria de uma integração, 02/09/2026): o juiz Sonnet
  reprovou DUAS rodadas por horário "~19:20" chutado e por ordem de arquivos afirmada sem medir (o `cp` do
  veredicto veio depois da prova no mesmo comando). Antídoto: rodar a prova num passo próprio,
  `stat -c '%n %y'` nos arquivos, e escrever a ENTREGA só com o que o `stat` mostrou — nunca tocar arquivo
  de veredicto depois da prova.
- Resumo de terceiros (vídeo, blog, "skill" extraída) NÃO entra na esteira
  sem auditoria na fonte: legendas automáticas garblam nomes ("Chyolos",
  "Burry") e fundem projetos distintos (caso Claw Code vs OpenClaw,
  30/08/2026). Conteúdo de YouTube se extrai com
  `python -m yt_dlp --skip-download --write-auto-subs --sub-langs "pt.*"`
  e limpa com grep/awk — WebFetch no YouTube devolve só o rodapé.
- O portão vira o vazamento (skill interna, 04/09/2026): para vetar uma senha nos .md eu escrevi o
  VALOR dela como literal no `prova.py` — e o `prova.py` é um dos arquivos publicados no canal da skill.
  O juiz da ENTREGA pegou. Antídoto: segredo só por SHA-256 em arquivo LOCAL fora do canal (ou padrão
  genérico), e o bloco de privacidade varre TODOS os arquivos que viajam, não só os .md; provar por
  mutação (injeta → VERMELHO). Registrar o incidente na memória com o total real de rodadas.
- Heredoc com aspas simples no Bash tool desta casa quebra com texto longo em pt-BR
  (05/09/2026, "unexpected EOF while looking for matching `''`"): arquivo de skill se grava
  pela ferramenta de escrita (sai em LF) e se confere com `file`, não por `cat <<'EOF'`.
- `$` seguido de dígito no corpo da skill VIRA ARGUMENTO (05/09/2026): ao invocar `/ocombo
  <texto>`, a linha de preços "Fable 5.1 \$10" carregou como "Fable 5.1 ocombo" — a doc diz que
  `\$1`, `\$2`… e `\$ARGUMENTS` são substituídos e que o literal se escreve `\$1.00`
  (https://code.claude.com/docs/en/skills). Antídoto: "USD 10" ou `\$10`; o `prova.py` veta `$<dígito>` cru.
- Comando de hook com caminho Windows de barra invertida (`C:\Users\...\python.exe`) NÃO executa
  (05/09/2026: 2 tentativas com log vazio; com `python` do PATH e barras normais o Stop bloqueou).
- Windows, duas vezes no mesmo dia (05/09/2026): console cp1252 derruba script que imprime acento
  (`reconfigure(encoding='utf-8')` no `__main__`); `claude.cmd` re-interpreta prompt com aspas por ARGUMENTO
  (engoliu `--output-format json`, custo "sem usage") — prompt por stdin.
- Dívida de um painel (06/09/2026): evidência "verde" cortada de execução
  INTERMEDIÁRIA (regrave DEPOIS do último conserto, com o nome que a rúbrica cita); triagem lê caminhos
  literais (`bug-1..5` e `scripts/x` com barra normal reprovam); suíte com banco compartilhado flakeia
  (repita a rodada, 0 tokens); árvore compartilhada = deploy de OUTRA sessão levou meu arquivo à VPS.

- **O portão de qualidade pega o próprio autor** (06/09/2026): `qualidade.py` recém-escrito acusou F823/F841 no `smoke_web.py` recém-escrito e F401 no `decisoes.py`; ruff com o padrão E/F devolveu só estilo (E701/E702/E741) até restringir a `F,E9`. Antídoto: o linter roda em si mesmo no `prova.py`, e seleciona correção, não estilo.
- **Caminho com CAIXA diferente no Windows = dois módulos** (06/09/2026): `scratchpad/c--users-x` x `C--Users-X` fez o Node carregar `@playwright/test` duas vezes e o runner acusou "two different versions". Antídoto: `os.path.realpath` antes de montar o comando.
- **Alegação na SOLUÇÃO sem `grep` no arquivo** (06/09/2026, ciclo da régua v5): o script que inseria 3 checagens no `prova.py` de outra skill morreu com SyntaxError no meio de um heredoc e eu escrevi "ganhou a checagem" sem abrir o arquivo; o juiz Sonnet foi à fonte e reprovou (r2). Antídoto: toda frase "o arquivo X tem Y" na SOLUÇÃO nasce de um `grep -c` rodado depois do último conserto; heredoc do Bash com `\x`/`\U` em literal quebra o script inteiro, e um script que quebra no meio deixa a metade anterior aplicada.
- **Push gatado no grep, não no exit code (09/09/2026, espelho público):** `prova_repo.py | grep FAIL && git push` deixou o push correr com o portão vermelho (o SKILL.md da casa tinha passado de 300 linhas em outra sessão) e a CI pública ficou vermelha um commit inteiro. Antídoto: `python tools/prova_repo.py; R=$?` e só empurrar com `R -eq 0`; e a skill da casa é fonte do espelho: se o `prova.py` dela está vermelho, o espelho nem se regenera.
- **Portao que AVISA e deixa passar (09/09/2026, ciclo dos modos):** `claude --effort banana -p` nao falha — imprime `Warning: Unknown --effort value 'banana' — ignoring it and using the default effort. Valid values: low, medium, high, xhigh, max.` e RODA a chamada (exit 0; o teste custou USD 0,47 em cache write do Opus 1M). Um argumento errado vira silenciosamente o padrao, e a rodada parece boa. Antidoto: lista fechada validada por nos ANTES de montar a linha (`modos.validar_effort`), e a lista vem do BINARIO (a doc oferecia `ultracode`, que a build 2.1.263 rejeita). Prova de maquina vence doc.
- **O smoke reprovava a TELA DE LOGIN de qualquer sistema (10/09/2026, achado por outra sessao):** o spec contava todo `console.error` como erro de JS, e um painel com sessao por cookie chama `/api/me`, toma 401 e o navegador loga `Failed to load resource ... 401`. O smoke da receita do proprio painel (Chrome real) passava verde — quando duas ferramentas discordam, a que reprova pode ser a errada. Antidoto: `assets/playwright/filtro.js` separa RELATO de request de ERRO de JS (`SMOKE_IGNORAR_STATUS`, padrao 401,403; 5xx nunca; `pageerror` sempre conta), o spec IMPRIME o que ignorou, e a prova de mutacao roda contra um servidor local de mentira: login com 401 passa, erro de JS de verdade reprova, tolerancia vazia reprova de novo.
- **Rubrica de ENTREGA julgada como PLANO (16/09/2026, ciclo notacao-magra):** a grelha escreveu C0 exigindo git log e evidencias do executor; o juiz reprovou o plano duas vezes (USD 0,51) porque um plano nunca tem essas provas - e no ciclo anterior o mesmo formato passou com N/A. Antidoto: criterio de evidencia vem marcado 'N/A no plano' e o C0 do plano cobra so a tabela Q->arquivo. Duas outras do mesmo dia: (a) python em heredoc do Git Bash com caminho `C:\Users` em string NAO-raw quebra com 'truncated \UXXXXXXXX' - script em arquivo, `r"..."`; (b) `a; juiz.py` rodou o juiz sobre um solucao.txt que o passo anterior nao gravou - encadeie com `&&`. (c) prova de obediencia com LLM varia: 1 vermelho no .30 virou A/B (completa 0/2, magra 2/2) antes de repetir o comando exato - repetir sem controle seria rolar dado ate dar verde.
- **Carimbo FALSO por 'APROVADO' solto em prosa (28/09/2026, ciclo de um site, achado pelo proprio juiz Sonnet):** o veredicto reprovou C0 e nao trazia a linha canonica `VEREDICTO:`; o fallback `\bAPROVADO\b` de `juiz.veredicto()` bateu em "apos o APROVADO r5 de la" (prosa sobre OUTRA instancia) e `juiz.py` gravou `aprovado.sha256` — `--carimbo` saiu 0 sobre um plano reprovado. Antidoto (commit na skill, teste `test_aprovado_solto_em_prosa_nunca_aprova`): sem linha canonica, `CRITERIO x: FAIL` ou `AJUSTE` = AJUSTE e APROVADO solto NUNCA aprova (vira INDEFINIDO). Tres outras do mesmo dia: (a) **escopo novo do dono colado como 'rodada 3' na instancia carimbada** (um site dentro da instancia de outro projeto) — o juiz reprovou C0: pedido novo passa por `porta.py` e ganha instancia propria; (b) **baseline sha256 de instancia ainda VIVA caduca**: o prova.bat de la regera PDF com `CreationDate` e regrava logs — meca so o corpo consumido, depois do carimbo, e nunca inclua artefato que o portao da instancia listada reescreve; (c) **heredoc com barra invertida** cobrou de novo: `\n` dentro de string Python virou quebra de linha e `\b` virou byte 0x08 dentro do solucao.txt (triagem nao ve; o executor da instancia contou bytes de controle) — script em arquivo via Write, e `bytes de controle = 0` como checagem barata antes do juiz.

