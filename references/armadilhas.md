# Armadilhas já pagas — lista completa (29/08 a 06/09/2026)

## As que mais custaram (estavam no SKILL.md até 09/09/2026)

- Portão verde com lista CURTA demais é suspeito: `ssh` sem `-n` dentro de `while read` engolia a lista e o deploy
  de uma integração fiscal ficou falso-verde de 30/08 a 02/09. Confira a CONTAGEM do portão com `git status`.
- Prova "verificado" só vale com artefato na pasta do juiz, gerado DEPOIS do último conserto, com o nome que a
  rúbrica cita; a seção ENTREGA é julgada como fato (`stat`, exit code), nunca como narrativa.
- Extração de módulo deixa SÍMBOLO ÓRFÃO que `node --check` e teste puro não pegam (bot caiu 2 min): a suíte
  executa a fiação e o `qualidade.py` (v4) roda antes do juiz.
- Segredo nunca vira literal em portão que viaja pelo canal (SHA-256 em arquivo local); `$` seguido de dígito no
  SKILL.md vira argumento; heredoc do Bash quebra com texto longo em pt-BR (grave por Write, confira com `file`).
- Resumo de terceiro (vídeo, blog) não entra na esteira sem auditoria na fonte; o juiz `claude -p` roda em sandbox
  e só lê a instância — copie o corpus e prove a cópia por SHA-256.


Movida do SKILL.md em 06/09/2026 (v4) para manter o corpo da skill magro; o SKILL.md guarda o ponteiro e as três mais caras. Nada foi apagado: cada item abaixo é o texto original.

- Portão verde com lista CURTA demais é suspeito (consertos de uma integração fiscal, 02/09/2026): o `--checar` do deploy
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
- A seção ENTREGA é julgada como fato, não como narrativa (auditoria de uma integração fiscal, 02/09/2026): o juiz Sonnet
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
- O portão vira o vazamento (skill de RH, 04/09/2026): para vetar uma senha nos .md eu escrevi o
  VALOR dela como literal no `prova.py` — e o `prova.py` é um dos arquivos publicados no canal do Drive.
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
- Dívida do painel interno (06/09/2026, dossiê fora do espelho): evidência "verde" cortada de execução
  INTERMEDIÁRIA (regrave DEPOIS do último conserto, com o nome que a rúbrica cita); triagem lê caminhos
  literais (`bug-1..5` e `scripts/x` com barra normal reprovam); suíte com banco compartilhado flakeia
  (repita a rodada, 0 tokens); árvore compartilhada = deploy de OUTRA sessão levou meu arquivo à VPS.

- **O portão de qualidade pega o próprio autor** (06/09/2026): `qualidade.py` recém-escrito acusou F823/F841 no `smoke_web.py` recém-escrito e F401 no `decisoes.py`; ruff com o padrão E/F devolveu só estilo (E701/E702/E741) até restringir a `F,E9`. Antídoto: o linter roda em si mesmo no `prova.py`, e seleciona correção, não estilo.
- **Caminho com CAIXA diferente no Windows = dois módulos** (06/09/2026): `scratchpad/C--users-user` x `C--Users-User` fez o Node carregar `@playwright/test` duas vezes e o runner acusou "two different versions". Antídoto: `os.path.realpath` antes de montar o comando.
- **Alegação na SOLUÇÃO sem `grep` no arquivo** (06/09/2026, ciclo da régua v5): o script que inseria 3 checagens no `prova.py` de outra skill morreu com SyntaxError no meio de um heredoc e eu escrevi "ganhou a checagem" sem abrir o arquivo; o juiz Sonnet foi à fonte e reprovou (r2). Antídoto: toda frase "o arquivo X tem Y" na SOLUÇÃO nasce de um `grep -c` rodado depois do último conserto; heredoc do Bash com `\x`/`\U` em literal quebra o script inteiro, e um script que quebra no meio deixa a metade anterior aplicada.
- **Ciclo das dívidas históricas do painel interno (06/09/2026, um ADR do projeto):** (a) manifesto de deploy que embarca TESTE de módulo que não embarca quebra a suíte de produção na importação e ninguém vê localmente — portão `manifesto-coerente` (todo import relativo de teste do manifesto aponta para arquivo do manifesto); (b) arquivo gitignorado que o código tracked importa (caixa no tronco) passa em casa e derruba a CI num checkout limpo — a CI materializa a fonte; (c) `subprocess.run(text=True)` no Windows troca o `\n` da entrada por `\r\n` e o `git check-ignore --stdin` não casa nada — mande BYTES; (d) segredo "histórico" só está morto depois do sha256 contra o `.env` vivo do serviço CERTO (o de outro serviço estava vivo); (e) ramo novo no pre-push varre a história inteira — `<sha> --not --remotes=<remoto>` é o que "só o que sai" significa.
- **Ciclo bigtech do painel interno (06/09/2026):** (a) `qualidade.py` estourava a linha de comando do Windows (WinError 206 / "Linha de comando muito longa" do shim .cmd do eslint, limite de 8 kB) — agora lotes de 40 arquivos; e entrava em `.claude/worktrees` de outras sessoes (1713 achados alheios) — `.claude` ignorado; (b) nome de passo do GitHub Actions com `: ` dentro (ex. "Auditoria (BLOQUEANTE: 0 high)") e YAML invalido e o run morre em 0 s "workflow file issue" — aspas no nome; (c) mudanca so no YAML nao dispara o workflow se o proprio arquivo nao esta em `paths`; (d) o axe em Chromium na CI achou 6 contrastes que o Chrome local nao mostrou (cartao com `opacity`) — a prova de a11y so vale na CI tambem; (e) `deploy-api.sh` [3/8] barra arquivo que existe na VPS e nunca esteve no git (ecosystem.config.cjs): resgatar o arquivo da VPS num commit proprio antes de versionar a mudanca.
- **Anonimizar a mao quebra frases (07/09/2026, espelho publico no GitHub):** a copia com nomes trocados por busca-e-troca deixou artigo dobrado (a preposicao + "o dono") e parentese dobrado, e ninguem viu. O certo: fonte unica + mapa ORDENADO fora do repo (`tools/publicar.py`, que sai 1 se uma troca nao casou) + portao que reprova termo privado E frase quebrada (`tools/prova_repo.py`, mesma varredura na CI). A triagem do juiz so enxerga caminhos DENTRO da instancia: cite `corpus/repo/...`, nunca o caminho da casa. `wsl bash -c "..."` com `$HOME` dentro de aspas duplas e expandido pelo Git Bash antes de chegar ao Linux: script em arquivo + MSYS_NO_PATHCONV=1.
- **Ciclo do espelho do Drive em outra máquina (08/09/2026):** (a) `python iniciar.py --help` CRIOU uma instância chamada `--help` dentro da skill (no Drive, a 22 min do cron da VPS) — o script agora recusa 1º argumento começando com `-` (teste em `test_v3.py`); leia o `__doc__` com `sed`, não rode para ver a ajuda; (b) `cmd.exe /c x.bat` no Git Bash vira `cmd.exe C:\ x.bat` (conversão de caminho do MSYS) e abre um cmd INTERATIVO que engole o resto do script — use `MSYS_NO_PATHCONV=1` ou o PowerShell com caminho COMPLETO (o `Set-Location` do PowerShell não muda o cwd que o `cmd.exe` filho enxerga); (c) `[int]$info.LastTaskResult` no verify do Agendador estoura com HRESULT (2147946720 = 0x800710E0, "operador recusou") e o verify morre em vez de reprovar — `[int64]`; (d) log de `.cmd` com `EXIT=%ERRORLEVEL%` dentro de `for` sem delayed expansion imprime o LITERAL — sub-rotina com `call :x` expande de verdade, e o teste exige `re.findall(r'EXIT=(\d+)')`; (e) "iniciei o serviço e montou" era falso: o relançamento só abriu a tela de login e o DONO logou 7 s depois — antes de escrever "eu fiz", procure no log de quem fez.
