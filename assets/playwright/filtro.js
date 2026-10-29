// Filtro do smoke de navegador (ocombo v9, 10/09/2026).
//
// POR QUE EXISTE: o spec contava QUALQUER linha `console.error` como erro de JS. A tela de login de
// qualquer sistema com sessao por cookie chama /api/me, toma 401 e o navegador loga
// "Failed to load resource: the server responded with a status of 401" — ou seja, o smoke reprovava a
// tela de login de todo mundo. Achado por outra sessao ao publicar um painel interno em 10/09/2026.
//
// O QUE ELE NAO AFROUXA: excecao de JS (`pageerror`) sempre conta; 5xx sempre conta e nunca pode ser
// tolerado, mesmo que alguem peca; 404 conta (recurso que falta e defeito). So sai da conta o RELATO de
// um request com status de sessao (401/403), que e comportamento normal de tela de login.
// Rigor total de volta: SMOKE_IGNORAR_STATUS= (vazio).

// Relato do proprio navegador sobre um request que falhou (nao e excecao de JS).
const RELATO_RECURSO = /^Failed to load resource: the server responded with a status of (\d{3})\b/;

function statusTolerados(valor) {
  const bruto = valor === undefined ? '401,403' : valor;
  return String(bruto)
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => Number.isInteger(n) && n >= 400 && n < 500);   // 5xx NUNCA se tolera
}

function ignoravel(texto, tolerados) {
  const m = RELATO_RECURSO.exec(String(texto || '').trim());
  if (!m) return false;                       // nao e relato de recurso: e erro de verdade
  return (tolerados || []).includes(parseInt(m[1], 10));
}

module.exports = { statusTolerados, ignoravel, RELATO_RECURSO };
