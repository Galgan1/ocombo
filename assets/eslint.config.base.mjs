// Config fixa do portao de qualidade do ocombo (scripts/qualidade.py). Flat config, ESLint 9+/10.
// Objetivo: pegar o que a suite nao pega - simbolo orfao (no-undef), variavel/import sem uso
// (no-unused-vars) e os erros de correcao do "recommended" - sem impor estilo. Sem import de pacote
// de proposito: o arquivo mora na skill e o eslint pode vir de outra pasta (OCOMBO_NODE_TOOLS); um
// `import '@eslint/js'` aqui resolveria relativo a ESTE arquivo e quebraria (medido em 06/09/2026).
// Fonte: https://eslint.org/docs/latest/use/configure/configuration-files

const nodeGlobals = {
  require: 'readonly', module: 'writable', exports: 'writable', __dirname: 'readonly', __filename: 'readonly',
  process: 'readonly', console: 'readonly', Buffer: 'readonly', setTimeout: 'readonly', clearTimeout: 'readonly',
  setInterval: 'readonly', clearInterval: 'readonly', setImmediate: 'readonly', URL: 'readonly',
  URLSearchParams: 'readonly', fetch: 'readonly', AbortController: 'readonly', TextEncoder: 'readonly',
  TextDecoder: 'readonly', structuredClone: 'readonly', globalThis: 'readonly', queueMicrotask: 'readonly',
};
const browserGlobals = {
  window: 'readonly', document: 'readonly', navigator: 'readonly', location: 'readonly', localStorage: 'readonly',
  sessionStorage: 'readonly', alert: 'readonly', confirm: 'readonly', prompt: 'readonly', FormData: 'readonly',
  Blob: 'readonly', File: 'readonly', FileReader: 'readonly', Image: 'readonly', HTMLElement: 'readonly',
  Event: 'readonly', CustomEvent: 'readonly', MutationObserver: 'readonly', IntersectionObserver: 'readonly',
  requestAnimationFrame: 'readonly', cancelAnimationFrame: 'readonly', history: 'readonly', screen: 'readonly',
  getComputedStyle: 'readonly', matchMedia: 'readonly', crypto: 'readonly', performance: 'readonly',
  CSS: 'readonly', DOMParser: 'readonly', Element: 'readonly', Node: 'readonly', NodeList: 'readonly',
  HTMLInputElement: 'readonly', MouseEvent: 'readonly', KeyboardEvent: 'readonly', ResizeObserver: 'readonly',
  WebSocket: 'readonly', Worker: 'readonly', XMLHttpRequest: 'readonly', Headers: 'readonly', Request: 'readonly',
  Response: 'readonly', AbortSignal: 'readonly', Notification: 'readonly', Audio: 'readonly', atob: 'readonly',
  btoa: 'readonly', self: 'readonly', open: 'readonly', scrollTo: 'readonly', innerWidth: 'readonly',
  innerHeight: 'readonly', devicePixelRatio: 'readonly', getSelection: 'readonly', speechSynthesis: 'readonly',
  SpeechSynthesisUtterance: 'readonly', Intl: 'readonly',
};
// service worker (PWA): sem isto todo sw.js da casa acusa no-undef falso em `caches`
// (medido em 07/09/2026 no superpads: 14 achados, zero defeitos). Fonte:
// https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerGlobalScope
const serviceWorkerGlobals = {
  caches: 'readonly', clients: 'readonly', registration: 'readonly', skipWaiting: 'readonly',
  importScripts: 'readonly', ServiceWorkerGlobalScope: 'readonly', ExtendableEvent: 'readonly',
  FetchEvent: 'readonly', CacheStorage: 'readonly', Cache: 'readonly', WorkerGlobalScope: 'readonly',
};
// vitest/jest: globais de teste
const testGlobals = {
  describe: 'readonly', it: 'readonly', test: 'readonly', expect: 'readonly', beforeEach: 'readonly',
  afterEach: 'readonly', beforeAll: 'readonly', afterAll: 'readonly', vi: 'readonly', jest: 'readonly',
};

// Subconjunto do eslint:recommended que aponta ERRO DE PROGRAMA (nao estilo).
const regrasCorrecao = {
  'no-undef': 'error',
  'no-unused-vars': ['error', { args: 'none', caughtErrors: 'none', varsIgnorePattern: '^_' }],
  'no-unreachable': 'error',
  'no-dupe-keys': 'error',
  'no-dupe-args': 'error',
  'no-dupe-else-if': 'error',
  'no-dupe-class-members': 'error',
  'no-duplicate-case': 'error',
  'no-redeclare': 'error',
  'no-const-assign': 'error',
  'no-func-assign': 'error',
  'no-class-assign': 'error',
  'no-import-assign': 'error',
  'no-global-assign': 'error',
  'no-self-assign': 'error',
  'no-ex-assign': 'error',
  'no-unsafe-negation': 'error',
  'no-unsafe-finally': 'error',
  'no-unsafe-optional-chaining': 'error',
  'use-isnan': 'error',
  'valid-typeof': 'error',
  'no-obj-calls': 'error',
  'no-sparse-arrays': 'error',
  'no-unexpected-multiline': 'error',
  'no-compare-neg-zero': 'error',
  'no-debugger': 'error',
  'no-delete-var': 'error',
  'no-empty-pattern': 'error',
  'no-empty-character-class': 'error',
  'no-invalid-regexp': 'error',
  'no-loss-of-precision': 'error',
  'no-setter-return': 'error',
  'no-shadow-restricted-names': 'error',
  'no-this-before-super': 'error',
  'no-unused-private-class-members': 'error',
  'no-useless-backreference': 'error',
  'constructor-super': 'error',
  'for-direction': 'error',
  'getter-return': 'error',
  'no-async-promise-executor': 'error',
  'no-new-native-nonconstructor': 'error',
  'no-nonoctal-decimal-escape': 'error',
  'no-octal': 'error',
  'no-with': 'error',
};

export default [
  {
    languageOptions: {
      ecmaVersion: 'latest',
      // OCOMBO_ESLINT_MODULE=1 vem do qualidade.py quando package.json tem "type": "module"
      sourceType: process.env.OCOMBO_ESLINT_MODULE === '1' ? 'module' : 'commonjs',
      globals: { ...nodeGlobals, ...browserGlobals, ...serviceWorkerGlobals, ...testGlobals },
    },
    rules: regrasCorrecao,
  },
  { files: ['**/*.mjs'], languageOptions: { sourceType: 'module' } },
  { files: ['**/*.cjs'], languageOptions: { sourceType: 'commonjs' } },
];
