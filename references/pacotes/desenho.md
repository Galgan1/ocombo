# Pacote desenho

Regua: `assets/rubricas/desenho.txt`. Abre com `python scripts/iniciar.py <pasta> --tipo desenho`, que grava no ESTADO a linha `Pacote       : desenho (ler references/pacotes/desenho.md)`. Os nomes das laminas nao mudam.

## Quando usar

Esta natureza cobre todo pedido cuja entrega e uma peca visual ou espacial que alguem vai olhar,
imprimir ou construir: planta, corte, maquete, cartaz, carta ilustrada, layout, croqui, desenho
tecnico. O sinal e o verbo do pedido: "desenha", "planta", "projeta", "ilustra", "compoe a arte",
"corta", "imprime". Se a entrega e so texto corrido (memorial sem desenho, carta sem arte), a
natureza e texto. Se a entrega e um numero ou uma afirmacao sobre o mundo real (precos, normas,
o que um terceiro faz), a natureza e pesquisa, mesmo que va virar tabela num PDF depois. Se a
entrega mexe num sistema no ar (publica, envia, apaga), a natureza e acao. Um pedido pode somar
desenho com pesquisa (planta que usa precos pesquisados) ou desenho com codigo (o gerador da
planta): ver "pedido misto" abaixo.

## O que a lamina 3 (akita) vira

O portao nasce ANTES da peca, nao depois. Isso quer dizer: primeiro escrevo o script que mede a
forma (cotas, folgas, cores, semelhanca contra o limiar da regua), rodo ele contra um rascunho
vazio ou contra a versao anterior, e provo o vermelho (o script tem de sair diferente de 0 nesse
estado). So depois desenho a peca de verdade e faco o script sair 0. Sem o vermelho provado antes,
o portao pode estar medindo qualquer coisa, inclusive nada.

## O que a lamina 4 (producao-senior) vira

A entrega fica dentro da instancia (pasta do ciclo), nunca em outro lugar por conta propria. Levar
a peca a um terceiro (mandar a alguem, publicar num site, imprimir de verdade), ou apagar uma
versao anterior, so acontece depois de um "sim" com a frase do dono registrado no ledger. Antes
disso a peca existe, mas ninguem fora da instancia a ve.

## O que conta como prova, e o que e [LEITURA]

Prova e o que um script mede contra um numero escrito na regua: cota bate, cor esta na paleta,
semelhanca abaixo do teto, sha256 do render bate com o que esta gravado, cruzes de corte contadas.
[LEITURA] e gosto: se a peca "ficou bonita", se o traco "parece" o estilo pedido, se um arquiteto
ou designer "aprova" a planta. [LEITURA] nunca decide sozinho: precisa de um segundo leitor de
outro tier citando a linha exata do entregavel que sustenta o PASS, e entra na regua com teto de
1/3 dos criterios de qualidade. No fecho ao dono, todo item que so um [LEITURA] sustentou aparece
com a frase "nao provado por maquina", nunca misturado com o que o script mediu.

- Jev: ferramenta opcional de nota, nunca portao; quando usado, a nota minima e combinada antes da rodada 1 e fica escrita na regua da instancia.

## prova.bat tipico desta natureza

```
@echo off
cd /d "%~dp0"
python peca\intacta.py corpus\antiga.sha256 || exit /b 1
python -m pytest peca -q -p no:cacheprovider || exit /b 1
python peca\valida.py peca\fonte.json || exit /b 1
python peca\desenha.py peca\fonte.json evidencias\peca.png --pdf --check || exit /b 1
python peca\confere_evidencias.py || exit /b 1
python <skill>\scripts\ledger.py pendentes <instancia> || exit /b 1
echo PROVA.BAT: VERDE
exit /b 0
```

## Regra do pedido misto

Vale a natureza do que o dono recebe. Se ele pede uma planta e o preco dos materiais entra so como
insumo, o ciclo e desenho e a pesquisa de precos e um passo interno dele (regua de desenho, com os
precos declarados com fonte). Se houver um script gerador da peca (o programa que desenha, nao a
peca em si), esse script tambem carrega o pacote codigo: lint e teste de unidade nele, alem da
regua de desenho na peca que ele produz. Os dois pacotes rodam juntos; nenhum substitui o outro.

## Armadilhas ja medidas em instancias reais

- Captura de tela de um app 3D fora da sessao interativa (GUI aberta numa maquina, print tirado
  por outro processo) so traz a moldura da janela, nunca o conteudo do viewport. Provar pelo
  render headless da mesma cena, nao pela imagem da janela.
- Rodar o portao pelo shell errado (`cmd /c prova.bat` chamado de dentro de um Bash POSIX) pode
  dar falso-verde. O portao roda sempre pelo interpretador nativo do arquivo, nunca encapsulado.
- Um script de medida nova pode ter o proprio bug de medida (por exemplo, decidir de que lado um
  objeto fica usando o centro errado como referencia) que so aparece num caso extremo da peca. O
  script que mede tambem precisa de teste de regressao proprio, nao so a peca que ele mede.
- Uma lista fechada por decisao do dono (referencias, itens permitidos, chave) pode crescer em
  silencio numa rodada nova sem reabrir a decisao que a fechou. Travar essa lista com um check que
  compara contra o valor combinado, nem a mais nem a menos.
- Um script de auditoria que so valida a peca nova, sem nunca reprovar a peca antiga com os
  defeitos que ele deveria pegar, pode ser um falso-positivo disfarcado: ele nao prova que a regua
  separa certo de errado, so que a peca nova passou por ele.
