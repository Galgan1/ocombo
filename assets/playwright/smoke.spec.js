// Smoke de navegador do ocombo (rubrica site C4): abre a pagina DE VERDADE, como o usuario ve.
// Confere o que o curl nao confere: a pagina renderizou, sem erro de JS no console, sem request 5xx,
// e com o texto/elemento esperado na tela. Uso (de qualquer pasta com @playwright/test instalado):
//   set SMOKE_URL=https://.../app/  &  set SMOKE_TEXTO=Entrar  &  npx playwright test --config <esta pasta>/playwright.config.js
// Variaveis: SMOKE_URL (obrigatoria), SMOKE_TEXTO (texto que tem de aparecer), SMOKE_SELETOR (opcional, css).
// Login e fluxo interno: copie este arquivo para o repo e acrescente passos; senha SEMPRE por variavel de ambiente.
// SMOKE_IGNORAR_STATUS (padrao "401,403"): status de SESSAO que o navegador relata no console e nao sao
// erro de JS — sem isso o smoke reprovava a tela de login de todo sistema com cookie (10/09/2026).
const { test, expect } = require('@playwright/test');
const { statusTolerados, ignoravel } = require('./filtro.js');

const URL_ALVO = process.env.SMOKE_URL;
const TEXTO = process.env.SMOKE_TEXTO || '';
const SELETOR = process.env.SMOKE_SELETOR || 'body';
const TOLERADOS = statusTolerados(process.env.SMOKE_IGNORAR_STATUS);

test('pagina abre sem erro de JS, sem 5xx e mostra o esperado', async ({ page }) => {
  test.skip(!URL_ALVO, 'SMOKE_URL nao definida');
  const errosConsole = [];
  const respostas5xx = [];
  const relatosIgnorados = [];
  page.on('pageerror', (e) => errosConsole.push(String(e)));   // excecao de JS: sempre conta
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const t = m.text();
    if (ignoravel(t, TOLERADOS)) relatosIgnorados.push(t); else errosConsole.push(t);
  });
  page.on('response', (r) => { if (r.status() >= 500) respostas5xx.push(r.status() + ' ' + r.url()); });

  const resp = await page.goto(URL_ALVO, { waitUntil: 'networkidle', timeout: 45000 });
  if (!URL_ALVO.startsWith('data:')) {  // data: nao devolve Response; serve para a prova de mutacao
    expect(resp, 'sem resposta').not.toBeNull();
    expect(resp.status(), 'status HTTP').toBeLessThan(400);
  }
  await expect(page.locator(SELETOR).first()).toBeVisible();
  if (TEXTO) await expect(page.getByText(TEXTO, { exact: false }).first()).toBeVisible();
  if (relatosIgnorados.length) {
    console.log('[smoke] ' + relatosIgnorados.length + ' relato(s) de sessao ignorado(s) (status '
                + TOLERADOS.join('/') + '): ' + relatosIgnorados[0]);
  }
  expect(respostas5xx, 'requests 5xx').toEqual([]);
  expect(errosConsole, 'erros de JS no console').toEqual([]);
});
