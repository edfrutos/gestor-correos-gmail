# Phase 32 — Contexto: acoplamiento actual entre `static/*.js`

Inventario tomado el 2026-09-08 sobre `static/app.js` (1940 líneas) y
`static/summary.js` (229 líneas). Ambos se cargan como *classic scripts* que
comparten el ámbito global (`index.html:350-351`), sin `type="module"` ni
bundler. No hay build tooling y la Fase 32 **no** lo introduce.

## Orden de carga

```
index.html → <script src="/static/app.js">      (define casi todo el estado global)
           → <script src="/static/summary.js">  (consume estado de app.js)
```

`summary.js` engancha listeners de nivel superior de inmediato (`sum-open`,
`sum-period`, `sum-ai`, `sum-copy`, `sum-dl`, `sum-x`, `sum-cn`), pero solo
**lee** estado de `app.js` dentro de callbacks (al abrir el resumen), cuando
`app.js` ya se ejecutó entero. `app.js` llama `init()` al final.

## Superficie compartida real (app.js → summary.js)

`summary.js` depende de estos símbolos definidos en `app.js`:

| Símbolo | Tipo | ¿Reasignado en app.js? | refs app.js / summary.js |
|---------|------|------------------------|--------------------------|
| `API` | `const` string | No | 25 / 1 |
| `activeEmails` | `let` array | **Sí** (`app.js:470,533,1097`) | 18 / 1 |
| `deleted` | `const` Set | No (solo mutado) | 17 / 1 |
| `aiStatus` | `let` object | **Sí** (`app.js:80`) | 3 / 2 |
| `CATS` | `let` object | **Sí** (`app.js:117,135`) | 15 / 4 |
| `esc` | function | — | shared helper |
| `toast` | function | — | shared helper |
| `gurl` | function | — | shared helper |
| `itemMeta` | function | — | shared helper |
| `messageSeverity` | function | — | shared helper |
| `severityRank` | function | — | shared helper |
| `severityReason` | function | — | shared helper |

## Estado mal ubicado

- `let summaryDays=30,summaryData=null;` se declara en `app.js:215` pero **solo**
  lo usa `summary.js` (9 y 28 refs respectivamente; 1 y 1 en app.js — la propia
  declaración). Es estado de `summary.js` viviendo en `app.js`.

## Dependencia HTML → JS global

`index.html` tiene 4 manejadores inline `onclick="togglePanel('...')"`
(`index.html:34,59,72,90`). Obligan a que `togglePanel` sea global. Todo lo
demás se cablea con `addEventListener`.

## Restricción: `tests/test_frontend_contract.py`

Es un test de **coincidencia literal de cadenas**: fija fragmentos exactos de
código. Cualquier reubicación de un símbolo compartido rompe las aserciones que
lo mencionan por su nombre desnudo. Aserciones afectadas y su *intención*
(que debe preservarse al actualizarlas):

| Test | Fragmento fijado | Intención |
|------|------------------|-----------|
| `test_periodic_summary_excludes_hidden_and_uses_loaded_messages` | `.filter(e=>!deleted.has(e.id)` | El resumen excluye ocultos |
| `test_periodic_summary_excludes_hidden_and_uses_loaded_messages` | `'activeEmails' in APP_JS` | El resumen usa correos cargados en memoria |
| `test_ai_summary_is_explicit_and_warns_before_remote_transmission` | `` fetch(`${API}/api/ai-summary` `` | Endpoint correcto |
| `test_ai_summary_is_explicit_and_warns_before_remote_transmission` | `aiStatus.remote&&!confirm(` | Avisa antes de enviar a proveedor remoto |
| `test_open_message_state_survives_attachment_hydration_render` | `const orig=activeEmails.find(ae=>ae.id===e.id)\|\|e;` | Abre el objeto vivo, no una copia |
| `test_attachment_hydration_updates_source_message_and_finishes_on_error` | `const sources=activeEmails.filter(item=>item.id===email.id);` | Hidrata todas las copias del mensaje |
| `test_frontend_assets_are_externalized_without_build_tooling` | lista de `<script>`/`<link>` | Activos externos, sin build tooling |

`SEVERITY_META`, `SEVERITY_ORDER`, `CATEGORY_SEVERITY`,
`CATEGORY_SEVERITY_REASON` también se hidratan desde `/api/config` en `app.js`
pero **no** los usa `summary.js` (solo vía `messageSeverity`/`severityRank`).
