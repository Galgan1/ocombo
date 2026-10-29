# Pacote texto

Régua: `assets/rubricas/texto.txt`. Abre com `python scripts/iniciar.py <pasta> --tipo texto`, que grava no ESTADO a linha `Pacote       : texto (ler references/pacotes/texto.md)`. Os nomes das lâminas não mudam.

## Quando uso

Uso este pacote quando a peça final é texto que alguém vai ler como texto — mensagem, post,
legenda, e-mail, roteiro de fala, verso de carta, resumo, relatório em prosa. A régua mede
forma (contagem), fato (fonte por item), voz (primeira pessoa, na peça que sai em nome do dono)
e tom (leitura).

Fronteira com as outras naturezas: se o pedido é sobre o que um terceiro diz ou fez (afirmação
que preciso provar com URL e trecho literal), a natureza é pesquisa, mesmo que a entrega saia
em texto — o pacote pesquisa manda ali. Se a peça é visual (imagem, PDF, planta, cartão), a
natureza é desenho, mesmo com texto dentro dela. Se o pedido termina em algo executado num
sistema (enviar, publicar, mexer numa tela), a natureza é ação. Uma mensagem avulsa sem ciclo
de juiz por trás é da skill `editor`, não deste pacote; aqui entra o texto que passa pelo combo
com rodada de juiz.

## O que a lâmina 3 (`akita`) vira aqui

Vira portão escrito ANTES de eu escrever a primeira palavra da peça: o script de forma (C1 da
régua) já existe, já tem o alvo (palavras por item, teto de bloco, o que o canal de destino não
renderiza) e eu rodo ele primeiro contra um rascunho vazio ou contra a versão anterior. Isso
tem de sair diferente de zero — o vermelho provado — antes de eu escrever a versão que deve
passar. Sem esse vermelho anexado em evidências, o portão não prova nada, só concorda comigo.

## O que a lâmina 4 (`producao-senior`) vira aqui

A entrega fica dentro da instância até segunda ordem. Mandar o texto a um terceiro (WhatsApp,
e-mail, post num canal), publicar em algum lugar no ar, ou apagar uma versão anterior só
acontece depois de um "sim" com a frase do dono registrada no ledger. Terminar o rascunho não é
terminar o ciclo; terminar o ciclo, quando envolve terceiro, é o "sim" + o envio provado.

## O que conta como prova

- Saída de um script com exit code (contagem de palavras/linhas, grep de voz, grep de custo,
  cruzamento de fonte por item), anexada em `evidencias/`.
- Fonte por item: item é o parágrafo ou o item numerado da peça. A fonte vai na linha do item
  ou num rodapé único, e o rodapé só vale com um mapa em `corpus/` (ex.: `corpus/fontes.md`)
  com a mesma numeração da peça, que o script cruza item a item; é o formato (b) do C2 da
  régua (`rodape sem mapa por item = FAIL`).
- Voz: o grep de primeira pessoa vale para a peça que sai em nome do dono (mensagem, e-mail,
  post dele); peça na voz de outro (personagem, carta de jogo, texto que um terceiro assina)
  fica N/A declarado na SOLUÇÃO com o motivo.
- Custo: o grep mira o custo da esteira (tokens, USD de modelo, `custo.log`), que nunca
  aparece; valor que é assunto da peça (orçamento, preço, pesquisa de mercado) não conta, e a
  SOLUÇÃO declara se a peça tem valores como assunto.
- O vermelho anterior ao verde, do mesmo script, também anexado — sem ele o portão não prova
  regressão nenhuma.
- Citação literal da linha da peça, quando o critério é [LEITURA] (ex.: tom, naturalidade): o
  segundo leitor aponta a linha exata que sustenta o PASS, não uma impressão geral.

O que é [LEITURA] é gosto medido por outro par de olhos, não por máquina, e tem teto de 1/3 dos
critérios de qualidade da régua. No fecho ao dono isso aparece com todas as letras, algo como
"o tom foi lido por um segundo leitor, não provado por máquina" — nunca como se fosse medição.

- Jev: ferramenta opcional de nota, nunca portão; quando usado, a nota mínima é combinada antes da rodada 1 e fica escrita na régua da instância.

## `prova.bat` típico desta natureza (exemplo genérico)

```bat
@echo off
cd /d "%~dp0"
python forma.py corpus\peca.txt > evidencias\prova.txt 2>&1
set E1=%ERRORLEVEL%
python fato_voz_custo.py corpus\peca.txt corpus\fontes.md >> evidencias\prova.txt 2>&1
set E2=%ERRORLEVEL%
set EXIT=0
if not "%E1%"=="0" set EXIT=1
if not "%E2%"=="0" set EXIT=1
echo EXIT=%EXIT% >> evidencias\prova.txt
type evidencias\prova.txt
exit /b %EXIT%
```

## Pedido misto

Vale a natureza do que o dono recebe. Se o pedido mistura texto com pesquisa (preciso apurar um
fato de terceiro antes de escrever), a régua de texto ainda julga a peça final, mas todo fato
apurado carrega a prova da régua de pesquisa (URL + trecho literal) antes de entrar no texto. Se
existe um script que GERA a peça (ex.: um gerador que monta o texto final a partir de um JSON),
esse script é código: o pacote código também vale para ele — lint e teste do gerador, além da
régua de texto sobre o que ele produz.

## Armadilhas já aprendidas (genéricas, sem nome próprio)

- Regra de voz e regra de custo escritas em linguagem natural ("não usar plural de time", "não
  falar de gasto") não seguram nada sozinhas; só o grep sobre o texto final prova que a regra
  foi respeitada, e a régua tem de exigir o comando, não a promessa.
- Critério de "soa bem" ou "está defensável" sem pedir citação da linha exata vira uma alegação
  do executor sem prova nenhuma anexada; toda leitura de gosto tem de vir com a linha citada, ou
  é FAIL por falta de evidência, não PASS por default.
- Rodar o portão por um `.bat` chamado de dentro de um shell diferente do esperado já deu
  falso-verde numa instância real: o comando saiu 0 sem ter rodado o que devia. O portão desta
  natureza roda por `python` direto, e o exit code do interpretador certo é o que entra na
  evidência, nunca o exit code do shell que chamou.
- Régua com critério que fala em "prova anexada" sem exigir que o arquivo exista, tenha mtime
  deste ciclo e contenha o dado alegado abre brecha para o executor apontar para uma evidência
  velha ou vazia; o critério de forma e o de fato têm de nomear o arquivo esperado.
- Regressão que só olha a peça mais recente esquece as peças de rodadas anteriores que já
  tinham passado; o critério de regressão desta natureza tem de re-rodar o mesmo script sobre o
  que já era verde, não só sobre o que mudou agora.
