// Smoke de navegador do ocombo (rubrica site C4): abre a pagina DE VERDADE, como o usuario ve.
// Confere o que o curl nao confere: a pagina renderizou, sem erro de JS no console, sem request 5xx,
// e com o texto/elemento esperado na tela. Uso (de qualquer pasta com @playwright/test instalado):
//   set SMOKE_URL=https://.../app/  &  set SMOKE_TEXTO=Entrar  &  npx playwright test --config <esta pasta>/playwright.config.js
// Variaveis: SMOKE_URL (obrigatoria), SMOKE_TEXTO (texto que tem de aparecer), SMOKE_SELETOR (opcional, css).
// Login e fluxo interno: copie este arquivo para o repo e acrescente passos; senha SEMPRE por variavel de ambiente.
const { test, expect } = require('@playwright/test');

const URL_ALVO = process.env.SMOKE_URL;
const TEXTO = process.env.SMOKE_TEXTO || '';
const SELETOR = process.env.SMOKE_SELETOR || 'body';

test('pagina abre sem erro de JS, sem 5xx e mostra o esperado', async ({ page }) => {
  test.skip(!URL_ALVO, 'SMOKE_URL nao definida');
  const errosConsole = [];
  const respostas5xx = [];
  page.on('pageerror', (e) => errosConsole.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errosConsole.push(m.text()); });
  page.on('response', (r) => { if (r.status() >= 500) respostas5xx.push(r.status() + ' ' + r.url()); });

  const resp = await page.goto(URL_ALVO, { waitUntil: 'networkidle', timeout: 45000 });
  if (!URL_ALVO.startsWith('data:')) {  // data: nao devolve Response; serve para a prova de mutacao
    expect(resp, 'sem resposta').not.toBeNull();
    expect(resp.status(), 'status HTTP').toBeLessThan(400);
  }
  await expect(page.locator(SELETOR).first()).toBeVisible();
  if (TEXTO) await expect(page.getByText(TEXTO, { exact: false }).first()).toBeVisible();
  expect(respostas5xx, 'requests 5xx').toEqual([]);
  expect(errosConsole, 'erros de JS no console').toEqual([]);
});
