// Teste puro do filtro do smoke (roda com `node test_filtro.js`, sem Playwright e sem rede).
// Nasceu de um achado de outra sessao em 10/09/2026: o smoke padrao reprovava a TELA DE LOGIN de
// qualquer sistema com sessao por cookie, porque o 401 de /api/me vira linha de console "error".
const assert = require('node:assert');
const { statusTolerados, ignoravel } = require('./filtro.js');

let testes = 0;
function t(nome, fn) { fn(); testes++; }

t('401 de checagem de sessao e ignoravel', () => {
  const s = statusTolerados();
  assert.ok(ignoravel('Failed to load resource: the server responded with a status of 401 ()', s));
  assert.ok(ignoravel('Failed to load resource: the server responded with a status of 401 (Unauthorized)', s));
  assert.ok(ignoravel('Failed to load resource: the server responded with a status of 403 (Forbidden)', s));
});

t('erro de JS de verdade NAO e ignoravel', () => {
  const s = statusTolerados();
  assert.ok(!ignoravel('Uncaught TypeError: x is not a function', s));
  assert.ok(!ignoravel('ReferenceError: fetchDados is not defined', s));
  assert.ok(!ignoravel('Uncaught (in promise) Error: 401 sem tratamento', s), 'excecao citando 401 conta');
});

t('404 e 5xx continuam contando', () => {
  const s = statusTolerados();
  assert.ok(!ignoravel('Failed to load resource: the server responded with a status of 404 (Not Found)', s));
  assert.ok(!ignoravel('Failed to load resource: the server responded with a status of 500 ()', s));
});

t('a lista vem do ambiente e pode ser esvaziada', () => {
  assert.deepStrictEqual(statusTolerados(''), []);
  assert.deepStrictEqual(statusTolerados('401'), [401]);
  assert.deepStrictEqual(statusTolerados('401, 403 ,404'), [401, 403, 404]);
  assert.deepStrictEqual(statusTolerados(undefined), [401, 403], 'padrao = sessao');
});

t('5xx nunca entra na lista, mesmo se pedirem', () => {
  assert.deepStrictEqual(statusTolerados('401,500,503'), [401]);
  assert.ok(!ignoravel('Failed to load resource: the server responded with a status of 500 ()',
                       statusTolerados('500')));
});

t('lista vazia faz o smoke voltar a ser rigoroso', () => {
  assert.ok(!ignoravel('Failed to load resource: the server responded with a status of 401 ()',
                       statusTolerados('')));
});

console.log('ok  ' + testes + ' teste(s) do filtro do smoke');
