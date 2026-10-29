# Pacote acao

Regua: `assets/rubricas/acao.txt`. Abre com `python scripts/iniciar.py <pasta> --tipo acao`, que grava no ESTADO a linha `Pacote       : acao (ler references/pacotes/acao.md)`. Os nomes das laminas nao mudam.

## Quando usar

Entra aqui todo pedido cuja entrega e uma MUDANCA DE ESTADO num sistema de terceiro que ja existe: preencher
ou editar um campo, publicar, enviar, marcar/etiquetar, apagar, pagar, configurar uma conta, aplicar uma
tag em lote. O que muda de mao e o ESTADO do sistema alheio (site, app, painel, caixa de e-mail), nao um
texto novo nem um numero calculado. A fronteira com `desenho` e `codigo`: se a acao e so subir um arquivo
que o proprio ciclo gerou (uma imagem, uma pagina), o gerador cai em `desenho` ou `codigo` e so o "subir"
cai em `acao`. A fronteira com `pesquisa`: navegar um site de terceiro para LER e citar e `pesquisa`; navegar
para MUDAR algo la e `acao`. A fronteira com `texto`: escrever a mensagem e `texto`; apertar "enviar" e `acao`.

## O que a lamina 3 (akita) vira

O portao nasce ANTES de tocar no sistema de terceiro, nunca depois. Antes de qualquer clique, existe um
script ou comando que sabe dizer, olhando uma captura vazia ou um estado ainda nao mudado, que a acao NAO
aconteceu (vermelho provado: o script sai diferente de 0 contra a captura do "antes" ou contra um rascunho
vazio). So depois desse vermelho gravado a acao roda de verdade. O mesmo script, rodado contra a captura do
"depois", vira o portao verde da entrega.

## O que a lamina 4 (producao-senior) vira

A entrega documental (capturas, script, solucao.txt) fica sempre na instancia — isso nunca espera "sim".
O que espera "sim" explicito do dono no ledger, com a frase dele registrada ANTES de executar, e qualquer
passo que: publique algo visivel a terceiro, envie mensagem ou e-mail, apague ou arquive em lote, pague ou
mexa em dinheiro, ou mude uma configuracao que outra pessoa vai ver. Um ensaio (modo leitura, sem aplicar)
nao precisa de "sim"; a aplicacao real precisa.

## O que conta como prova

- captura de tela ou texto de pagina do ANTES e do DEPOIS, em evidencias/; em acao sem tela (API, IMAP,
  script), o log de texto do script com o estado do antes e do depois (contagens, ids) vale como captura;
- um script que confere, na captura do depois, as strings que provam a mudanca (exit code, nao opiniao);
- a lista exata do que foi mexido, batendo campo a campo com o que a TAREFA pediu;
- ausencia de credencial em qualquer arquivo (grep vazio, saida anexada);
- quando o executor nao tem navegador, a declaracao de que o maestro executou, escrita no ESTADO antes do
  clique, nao depois para justificar; acao sem tela nao tem navegador a declarar, e o C5 da regua fica
  N/A declarado na SOLUCAO, com o comando que executou a acao.

O que e [LEITURA] nessa natureza: se o resultado final "faz sentido" para quem olha a tela — coerencia
visual, tom, se o layout de terceiro nao quebrou — e gosto, nao medida; entra como [LEITURA] com um segundo
leitor de outro tier citando a linha da captura, teto de 1/3 dos criterios de qualidade. No fecho da
entrega isso aparece como "nao provado por maquina": por exemplo, se um botao so aparece a um visitante no
aplicativo e a sessao nao tem aparelho para testar, o fecho diz isso sem fingir que foi medido.

- Jev: ferramenta opcional de nota, nunca portao; quando usado, a nota minima e combinada antes da rodada 1 e fica escrita na regua da instancia.

## prova.bat tipico

```
@echo off
cd /d "%~dp0"
python prova.py
exit /b %ERRORLEVEL%
```

Onde prova.py confere, contra a captura ou o texto de pagina do depois, as strings esperadas e a ausencia
de credencial nos arquivos da instancia, e sai 1 se qualquer uma faltar.

## Pedido misto

Vale a natureza do que o dono recebe. Se o pedido junta gerar uma peca nova (texto, imagem) com subir ou
publicar essa peca num sistema de terceiro, o pacote da peca (texto/desenho) rege a peca em si e o pacote
`acao` rege so o passo de publicar/enviar. Se existe um script gerador por tras da acao (por exemplo, o que
varre uma caixa e aplica etiquetas), esse script tambem cai no pacote `codigo` — lint e teste valem para
ele, alem da captura de antes/depois exigida por `acao`.

## Armadilhas genericas (aprendidas em instancias reais)

- Um classificador automatico de seguranca pode barrar o comando que registra o "sim" no ledger; quando
  isso acontece, a frase do dono dita na conversa vale como registro e fica declarada no ESTADO ate poder
  ser gravada — nao se finge que o ledger passou.
- Digitar num campo de um site de terceiro sem antes clicar nele pode acionar atalhos de teclado da propria
  pagina e abrir paineis indesejados; sempre clicar no campo certo antes de digitar qualquer texto.
- Um formulario de terceiro pode falhar de forma transitoria com uma mensagem generica de "tente novamente
  mais tarde"; o incidente entra na SOLUCAO e se busca um caminho alternativo do mesmo site em vez de
  insistir cegamente no mesmo passo.
- Rodar o portao por um shell diferente do esperado (por exemplo `cmd /c` dentro de outro terminal) ja deu
  falso-verde numa instancia real; o portao roda sempre pelo interpretador direto, nunca por um wrapper de
  outro shell.
- Quando a acao depende de um componente que varia entre rodadas (por exemplo, um classificador probabi-
  listico), o numero do ensaio e o numero da aplicacao real podem nao bater; a diferenca se declara na
  SOLUCAO em vez de ser escondida ou arredondada para o numero que "ficaria bonito".
