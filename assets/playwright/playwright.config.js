// Config minima do smoke de navegador (assets/playwright/smoke.spec.js). Chromium headless, 1 tentativa,
// relatorio em linha + JSON em PW_JSON (para anexar na instancia). Instalar uma vez:
//   npm i -D @playwright/test && npx playwright install chromium
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: __dirname,
  testMatch: /smoke\.spec\.js/,
  timeout: 60000,
  retries: 0,
  workers: 1,
  reporter: process.env.PW_JSON ? [['line'], ['json', { outputFile: process.env.PW_JSON }]] : [['line']],
  use: {
    headless: true,
    ignoreHTTPSErrors: false,
    screenshot: 'only-on-failure',
    trace: 'off',
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
