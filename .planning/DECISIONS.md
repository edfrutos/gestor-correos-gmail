# Decisions

## ADR-001 — Mantener Ejecución Local

**Date:** 2026-05-31  
**Status:** Accepted

La herramienta seguirá ejecutándose en local mediante `.venv/bin/python server.py`.

**Rationale:** Gmail contiene datos privados y el valor actual no requiere despliegue público. Mantenerla local reduce superficie de ataque, coste operativo y complejidad de autenticación.

**Consequences:** cualquier API local debe tratarse como sensible. No se debe abrir CORS de forma indiscriminada. Las dependencias Python se instalan en `.venv` para evitar modificar el Python de Homebrew.

## ADR-002 — Gmail Readonly por Defecto

**Date:** 2026-05-31  
**Status:** Accepted

La integración Gmail mantendrá `https://www.googleapis.com/auth/gmail.readonly`.

**Rationale:** la herramienta actual consulta, clasifica y exporta; no necesita modificar Gmail. Ampliar scopes obligaría a revisar seguridad y UX.

**Consequences:** archivar, borrar o etiquetar correos queda fuera de v1.

## ADR-003 — Seguridad Antes de Funcionalidad Nueva

**Date:** 2026-05-31  
**Status:** Accepted

La primera fase se centrará en CORS, validación, secretos y render seguro antes de añadir persistencia o inteligencia.

**Rationale:** la API local accede a Gmail autenticado; nuevas funciones sobre una base insegura amplificarían el riesgo.

**Consequences:** paneles avanzados, reglas editables y resúmenes quedan tras el hardening inicial.

## ADR-004 — Persistencia Local Antes que Cloud

**Date:** 2026-05-31  
**Status:** Accepted

La persistencia se implementa localmente mediante JSON normalizado y escritura atómica. SQLite queda como opción si el estado crece.

**Rationale:** fuentes, reglas, ocultados y preferencias necesitan sobrevivir entre sesiones sin exponer datos fuera del equipo.

**Consequences:** `app_state.json` guarda fuentes, reglas editables, IDs ocultos y preferencias, pero no contenido Gmail.

## ADR-005 — AI Opcional y Transmisión Explícita

**Date:** 2026-06-09
**Status:** Accepted

La integración AI permanece desactivada sin configuración y sólo recibe un resumen operativo cuando el usuario solicita la acción.

**Rationale:** cualquier proveedor remoto amplía la frontera de privacidad y debe ser una decisión visible, no un efecto secundario.

**Consequences:** la API key permanece en Python, los proveedores remotos requieren confirmación y Gmail nunca se envía automáticamente.

## ADR-006 — Frontend Modular sin Build Tooling

**Date:** 2026-06-09
**Status:** Accepted

La interfaz separa HTML, CSS, aplicación principal y resúmenes en activos estáticos servidos desde una lista cerrada.

**Rationale:** la separación reduce el coste de mantenimiento sin introducir un pipeline de compilación innecesario para una herramienta local.

**Consequences:** los activos nuevos deben añadirse explícitamente a `STATIC_FILES`; una migración a framework requiere una decisión posterior.

## ADR-007 — Borrado Permanente Aislado

**Date:** 2026-06-10
**Status:** Accepted

El tratamiento final de ocultos incluirá borrado inmediato, permanente e irreversible mediante `users.messages.delete`.

**Rationale:** el usuario ha elegido explícitamente borrar del servidor Gmail sin pasar por Papelera. Gmail exige para ello el scope restringido `https://mail.google.com/`; `gmail.modify` no permite esta operación.

**Consequences:** el cliente normal conservará `gmail.readonly`. El permiso destructivo usará un token separado, estará desactivado por defecto, sólo aceptará IDs actualmente ocultos, limitará cada lote a 20 mensajes y exigirá una frase de confirmación con el número exacto.

**Sources:**
- https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/delete
- https://developers.google.com/workspace/gmail/api/auth/scopes

## ADR-008 — Vista de Correo en Modal (supera el expandir-inline)

**Date:** 2026-06-16
**Status:** Accepted

La lectura de un correo se abre en un modal dedicado ("subventana"). Se retira la
tarjeta expandible inline y el `Set` `openMessages` deja de gobernar el render;
la hidratación de adjuntos pasa a `openEmailModal()`.

**Rationale:** el expandir-inline mezclaba lista y detalle, forzaba re-render de
toda la cola al abrir un correo y complicaba la supervivencia del estado tras
hidratar adjuntos. El modal aísla el detalle y simplifica el ciclo de render.

**Consequences:** `test_frontend_contract.py::test_open_message_state_survives_attachment_hydration_render`
queda obsoleto (aserción sobre el patrón inline) y se sanea en la Fase 31.

## ADR-009 — Exportación a `/exports` (supera el streaming de descarga)

**Date:** 2026-06-12
**Status:** Accepted

`/api/messages/export` escribe el `.eml`/`.zip` en el directorio persistente
`/exports` y responde JSON (`{status,file,path,type}`) en vez de transmitir el
fichero como descarga del navegador.

**Rationale:** habilita el lector EML integrado, el panel "Exportaciones locales"
y el uso headless/VPN sin diálogos de descarga del navegador.

**Consequences:** `test_handle_messages_export_single_eml` y `..._zip` quedan
obsoletos (esperan `message/rfc822` / `application/zip` en streaming) y se sanean
en la Fase 31.

## ADR-010 — Troceado y Cota de Lotes en Archivado/Etiquetado

**Date:** 2026-09-08
**Status:** Accepted

`archive_messages` y `apply_label` trocean los IDs en tandas de
`BATCH_MODIFY_CHUNK = 100` (helper `_batch_modify_chunked`, serializado bajo
`_api_lock`). Los handlers `/api/messages/archive` y `/api/messages/label`
rechazan lotes de más de `MAX_BATCH_MODIFY = 1000`. La UI (`guardBatchSize`)
corta en 1000 y pide confirmación a partir de 200.

**Rationale:** Gmail limita `users.messages.batchModify` a 1000 IDs por petición;
el código enviaba toda la selección en una sola llamada, sin cota ni troceado,
de modo que >1000 fallaba con 400 y 200–1000 iba en una petición gigante sin
granularidad. El borrado permanente ya troceaba (`DELETE_EXECUTION_CHUNK = 20`);
esto lleva el mismo criterio a las operaciones no destructivas.

**Consequences:** una tanda que falle deja las anteriores ya aplicadas en Gmail
(sin rollback); el ocultado local solo ocurre si la llamada completa no lanzó.
No se implementa progreso incremental en la UI (una única petición HTTP): se opta
por aviso previo + texto informativo, coherente con la arquitectura local-first
sin streaming.

## ADR-011 — Espacio de Nombres `App` para el Estado Compartido del Front

**Date:** 2026-09-08
**Status:** Accepted (Fase 32, Stage A+B; Stage C pendiente/opcional)

`static/shared.js` (classic script, cargado antes que `app.js` y `summary.js`,
registrado en `STATIC_FILES`) define `window.App = { api, state:{deleted}, config }`.
`app.js` publica en `App` el estado que `summary.js` necesita leer; `summary.js`
accede siempre vía `App.*`, nunca por variable global desnuda. Sin build tooling
ni `type="module"`.

Alcance aplicado: `API` → `App.api`; `deleted` → `App.state.deleted` (ambos
`const`/no reasignados, coste ~2 líneas en `app.js`). `summaryDays`/`summaryData`
—estado que solo usa `summary.js`— se reubican en ese archivo. Los `onclick`
inline de `index.html` se sustituyen por `data-panel` + listener.

Fuera de alcance por ahora (Stage C): `activeEmails`, `aiStatus`, `CATS` se
reasignan en `app.js` (~36 sitios); moverlos exige repunte total o accessors y
smoke manual del plan humano. `app.js` no tiene tests de runtime, así que se
prioriza el incremento de bajo riesgo.

**Rationale:** `test_frontend_contract.py` fija fragmentos literales de código;
un refactor a módulos ES rompería decenas de aserciones y su valor como guardarraíl.
`App` como objeto plano da acceso explícito y documentado a la superficie
compartida con cambio mínimo.

**Consequences:** 3 aserciones de `test_frontend_contract.py` pasan a nombrar el
acceso vía `App` (intención preservada: excluye ocultos, endpoint correcto, avisa
antes de envío remoto). Nuevo `test_shared_namespace_is_declared_and_documented`.
Regla para el front (recogida en `AGENTS.md`): estado nuevo que cruce
`app.js`↔`summary.js` va en `App`, no en el global.
