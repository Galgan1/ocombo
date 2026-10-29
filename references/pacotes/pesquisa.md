# Pacote pesquisa

Régua: `assets/rubricas/pesquisa.txt`. Abre com `python scripts/iniciar.py <pasta> --tipo pesquisa`, que grava no ESTADO a linha `Pacote       : pesquisa (ler references/pacotes/pesquisa.md)`. Os nomes das lâminas não mudam.

## Quando uso este pacote

- O pedido cai aqui quando o resultado é uma afirmação sobre algo fora do meu controle: um concorrente, um fornecedor, uma lei, um preço de mercado, "como os outros fazem isso", o histórico de um terceiro, a viabilidade técnica de algo que eu não vou construir agora.
- Fronteira com **desenho**: pesquisa levanta fatos e compara; desenho decide uma forma (planta, arte, estratégia visual) a partir de fatos já levantados. Quando o pedido pede as duas coisas, o pacote de desenho herda os fatos como corpus, e a rubrica de pesquisa cobre só o levantamento.
- Fronteira com **texto**: pesquisa não produz o texto final que vai a alguém; ela alimenta um texto, que aí segue o pacote texto (voz, tom, portão de forma próprios).
- Fronteira com **ação**: pesquisa só lê. A partir do momento em que um passo muda algo — uma conta, uma configuração, um envio —, esse passo é ação, mesmo que tenha nascido de uma pesquisa.

## O que a lâmina 3 (akita) vira nesta natureza

- Vira um portão escrito ANTES de eu escrever qualquer palavra do entregável: um script que mede a forma do rascunho (seções obrigatórias, URL + trecho por afirmação, número com comando ao lado, a seção "não provado") e sai vermelho contra um rascunho vazio ou incompleto. Só depois do vermelho provado eu escrevo o conteúdo.
- Esse portão nunca julga se um fato é verdadeiro, só se a forma exigida está presente (URL+trecho na linha certa, número com comando anexado, seção obrigatória existe). A verdade do fato é papel dos critérios [MEDIDO]/[LEITURA] da régua, não do portão de forma.

## O que a lâmina 4 (producao-senior) vira nesta natureza

- A entrega, por padrão, fica dentro da instância: um arquivo, o `corpus/` com os trechos salvos e as `evidencias/` com os comandos que geraram cada número.
- Levar a pesquisa a terceiro (mandar para alguém fora, publicar, citar num texto que sai da casa) ou apagar algo já salvo só acontece com "sim" explícito registrado no ledger. Enquanto esse "sim" não existe, a pesquisa é material interno, mesmo com o juiz em APROVADO.

## O que conta como prova

- URL + trecho literal salvo em `corpus/`, na mesma linha da afirmação que ele sustenta.
- Um comando ou script em `evidencias/` para todo número que aparece no entregável — nunca um número de cabeça.
- Uma seção própria listando o que foi procurado e não achado.
- Uma amostra das fontes reaberta por um agente de outro tier, citando a linha do entregável que ela sustenta.
- [LEITURA] é o rótulo para o que a máquina não mede sozinha — peso de um argumento, relevância de uma fonte, qualidade de uma comparação. Ele exige um segundo leitor de outro tier citando a linha; sem essa citação, vira FAIL, nunca PASS por omissão.
- No fecho, tudo que ficou em [LEITURA] ou sem fonte checável por máquina aparece na seção "não provado por máquina" — nunca escondido no corpo do texto como se fosse fato medido.
- Jev: ferramenta opcional de nota, nunca portão; quando usado, a nota mínima é combinada antes da rodada 1 e fica escrita na régua da instância.

## `prova.bat` típico desta natureza

```
python prova.py --entregavel pesquisa.md --corpus corpus/ --evidencias evidencias/
REM checa: secao "nao provado" existe; toda linha com URL tem corpus/ correspondente;
REM todo numero (por regex de digito) tem comando irmao em evidencias/comandos.txt;
REM contagem de perguntas ao dono na rodada <= 3.
```

## A regra do pedido misto

Vale a natureza do que o dono recebe. Se o pedido é "pesquisa X e me entrega um texto pronto", o entregável final é texto e segue o pacote texto, com a pesquisa como corpus de apoio (ainda com URL+trecho, ainda com a seção "não provado"). Se houver um script que gera parte da pesquisa — um coletor, um raspador, um leitor de planilha —, esse script entra também no pacote código (lint, teste), mesmo que o resultado publicado seja pesquisa.

## Armadilhas já aprendidas

- Um número derivado de uma fonte pode admitir duas leituras que não batem entre si — por exemplo, um percentual lido direto do arquivo e a soma de faixas do mesmo arquivo dando outro valor. A saída correta é citar os dois números com a fonte de cada um, não "corrigir" o arquivo de evidência para fazer bater: a regressão exige que a evidência fique intacta.
- Critério de forma vago ("uma linha", "explicado em meia linha", "falsificável") é trapaceável — vira PASS por leitura generosa do juiz. Todo critério de forma precisa virar uma contagem exata (contagem de linhas, contagem de palavras, expressão regular) antes da rodada 1, não depois que o juiz já reprovou por vaguidão.
- Rodar o portão por um atalho de shell que reabre um interpretador interativo em vez de executar o script pode devolver código de saída 0 sem rodar nada — um falso-verde. O portão só conta quando a saída contém a linha de confirmação do próprio script, nunca só o código de saída do shell que o chamou.
- Uma afirmação sobre terceiro citada de fonte secundária (uma matéria que resume outra fonte) pode estar desatualizada ou simplesmente errada frente à fonte primária; conferir a fonte primária derruba a citação secundária com uma frequência que compensa o esforço.
- O que um agente de varredura relata como "já coberto" ou "já em funcionamento" precisa ser cruzado com uma medição direta (um registro, uma configuração, um arquivo de estado) — o relato de um agente sobre o estado de algo não é, sozinho, a prova desse estado.
