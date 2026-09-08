// ── App: espacio de nombres compartido del frontend ───────
// Se carga ANTES de app.js y summary.js (ver index.html). Classic script, sin
// build tooling. app.js publica aquí el estado que summary.js necesita leer;
// summary.js accede siempre vía `App.*`, nunca por variable global desnuda.
//   App.api            → base de la API local (string, la fija app.js)
//   App.state.deleted  → Set de IDs de correos ocultos localmente
// Pendiente Stage C (Fase 32): App.state.activeEmails, App.state.aiStatus,
// App.config.CATS — hoy summary.js aún los lee como global de app.js.
window.App = window.App || {
  api: '',
  state: { deleted: null },
  config: {},
};
