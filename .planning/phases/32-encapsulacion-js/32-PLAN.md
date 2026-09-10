---
phase: 32
plan_id: 32-PLAN
title: Encapsulación JS
milestone: v8
depends_on: [30, 31, 33]
requirements_addressed: [MNT-02]
files_modified:
  - static/shared.js        # nuevo (Stage B)
  - static/app.js
  - static/summary.js
  - index.html
  - server.py
  - tests/test_frontend_contract.py
  - .planning/STATE.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
  - .planning/DECISIONS.md
autonomous: false   # Stage C exige smoke manual (TESTING_HUMANO §2–§6)
---

# Phase 32 Plan: Encapsulación JS

## Objetivo

Reducir las dependencias cruzadas por variable global entre `static/app.js` y
`static/summary.js`: hacer explícita la superficie compartida y moverla a un
espacio de nombres único (`App`), sin introducir build tooling ni `type="module"`
y preservando la **intención** de `tests/test_frontend_contract.py`.

Ver inventario de acoplamiento en `32-CONTEXT.md`.

## Must Haves

- Sin bundler, sin `import`/`export`, sin `type="module"`. Siguen siendo classic
  scripts servidos desde la allowlist `STATIC_FILES`.
- `summary.js` no vuelve a leer un identificador global desnudo definido en
  `app.js`; accede a la superficie compartida vía `App.*`.
- Cada aserción de `test_frontend_contract.py` que se toque conserva su
  intención (endpoint correcto, excluye ocultos, avisa antes de envío remoto,
  abre el objeto vivo, activos externos). Se documenta el cambio en el commit y
  en ADR-011.
- `pytest` verde, `node --check` sobre ambos JS, y smoke manual del plan humano
  (§2 Búsqueda, §3 Gestión Gmail, §4 Automatización, §5 IA, §6 Exportación/lector)
  para las stages que tocan estado reasignado.
- Sin cambios de comportamiento observable en la UI.

## Estrategia por stages

Se ejecuta en incrementos de riesgo creciente. Stage A y B son de bajo riesgo y
se recomiendan en esta fase; Stage C es opcional y se ejecuta solo con visto
bueno explícito y smoke manual completo.

---

## Stage A — Relocación y documentación (riesgo casi nulo)

<task id="32-A1" name="Mover estado propio de summary.js fuera de app.js" type="execute">
  <read_first>
    <file>static/app.js</file>            <!-- línea 215 -->
    <file>static/summary.js</file>
  </read_first>
  <action>
    Borrar `let summaryDays=30,summaryData=null;` de `app.js:215`. Añadir esa
    misma línea al principio de `summary.js` (antes de `countBy`). Verificar que
    `app.js` no referencia `summaryDays`/`summaryData` en ningún otro punto
    (grep: solo la declaración).
  </action>
  <acceptance_criteria>
    <criterion>`grep -c "summaryD" static/app.js` == 0</criterion>
    <criterion>`summary.js` declara `summaryDays`/`summaryData` en su primera línea de código</criterion>
    <criterion>`node --check static/summary.js` OK</criterion>
  </acceptance_criteria>
</task>

<task id="32-A2" name="Cabecera SHARED SURFACE en ambos archivos" type="execute">
  <action>
    Añadir al inicio de `app.js` un bloque de comentario
    `// ── SHARED SURFACE (consumida por summary.js) ──` enumerando: `App.api`,
    `App.state.activeEmails`, `App.state.deleted`, `App.state.aiStatus`,
    `App.config.CATS`, y las funciones helper compartidas (`esc`, `toast`,
    `gurl`, `itemMeta`, `messageSeverity`, `severityRank`, `severityReason`).
    Añadir en `summary.js` un comentario recíproco
    `// Depende de App.* y de las funciones helper de app.js (ver app.js).`
  </action>
  <acceptance_criteria>
    <criterion>Ambos archivos contienen la cabecera; el texto lista los símbolos exactos</criterion>
  </acceptance_criteria>
</task>

<task id="32-A3" name="Eliminar manejadores inline de index.html" type="execute">
  <read_first><file>index.html</file></read_first>
  <action>
    Sustituir los 4 `onclick="togglePanel('X')"` (`index.html:34,59,72,90`) por
    `data-panel="X"` en el mismo `.ph`. En `app.js`, junto al resto de cableado
    de listeners, añadir:
    `document.querySelectorAll('.ph[data-panel]').forEach(h=>h.addEventListener('click',()=>togglePanel(h.dataset.panel)));`
    `togglePanel` permanece como función de nivel superior (uso interno), pero
    deja de ser una dependencia implícita del HTML.
  </action>
  <acceptance_criteria>
    <criterion>`grep -c "onclick" index.html` == 0</criterion>
    <criterion>Los 4 paneles (`p-snd`, `p-cat`, `p-exp`, `p-rules`) siguen plegando/desplegando</criterion>
  </acceptance_criteria>
</task>

<task id="32-A4" name="Contract test: cabecera y ausencia de inline handlers" type="execute">
  <read_first><file>tests/test_frontend_contract.py</file></read_first>
  <action>
    En `test_frontend_assets_are_externalized_without_build_tooling` añadir
    `assert 'onclick=' not in html`. Añadir un test nuevo
    `test_shared_surface_is_documented` que compruebe que `app.js` contiene
    `SHARED SURFACE` y que `summary.js` no declara `summaryDays`/`summaryData`
    fuera de su propia primera línea.
  </action>
  <acceptance_criteria>
    <criterion>`pytest -q` verde</criterion>
  </acceptance_criteria>
</task>

---

## Stage B — Espacio de nombres `App` para el estado compartido no reasignado (riesgo bajo)

`API` (const, nunca reasignado) y `deleted` (const Set, solo mutado) se pueden
exponer en `App` sin tocar el cuerpo de `app.js`.

<task id="32-B1" name="Crear static/shared.js y registrarlo" type="execute">
  <read_first>
    <file>server.py</file>                <!-- STATIC_FILES, líneas 65-68 -->
    <file>index.html</file>              <!-- líneas 348-351 -->
  </read_first>
  <action>
    Crear `static/shared.js` con:
    `window.App=window.App||{api:'',state:{activeEmails:null,deleted:null,aiStatus:null},config:{}};`
    Registrar `'/static/shared.js'` en `STATIC_FILES` de `server.py`.
    Añadir `<script src="/static/shared.js"></script>` en `index.html`
    **antes** de `app.js`.
  </action>
  <acceptance_criteria>
    <criterion>`GET /static/shared.js` devuelve 200 y `text/javascript`</criterion>
    <criterion>El `<script>` de shared.js precede al de app.js en index.html</criterion>
    <criterion>`node --check static/shared.js` OK</criterion>
  </acceptance_criteria>
</task>

<task id="32-B2" name="Publicar API y deleted en App desde app.js" type="execute">
  <read_first><file>static/app.js</file></read_first>
  <action>
    Tras `const API = '';` añadir `App.api=API;`.
    Tras `const deleted=new Set(),selected=new Set(),openMessages=new Set();`
    añadir `App.state.deleted=deleted;`.
    No se cambia ninguna otra referencia en `app.js` (siguen usando `API` y
    `deleted` locales, que son las mismas referencias).
  </action>
  <acceptance_criteria>
    <criterion>`App.api` y `App.state.deleted` quedan asignados en app.js</criterion>
    <criterion>Diff en app.js == 2 líneas añadidas</criterion>
  </acceptance_criteria>
</task>

<task id="32-B3" name="Repuntar summary.js a App.api / App.state.deleted" type="execute">
  <read_first><file>static/summary.js</file></read_first>
  <action>
    En `summary.js`: `!deleted.has(e.id)` → `!App.state.deleted.has(e.id)`
    (1 sitio, `visibleDatedItems`). `` `${API}/api/ai-summary` `` →
    `` `${App.api}/api/ai-summary` `` (1 sitio, `requestAiSummary`).
  </action>
  <acceptance_criteria>
    <criterion>`grep -E "[^.]\bdeleted\b|[^.]\bAPI\b" static/summary.js` == 0</criterion>
    <criterion>`node --check static/summary.js` OK</criterion>
  </acceptance_criteria>
</task>

<task id="32-B4" name="Contract test: actualizar aserciones de Stage B" type="execute">
  <read_first><file>tests/test_frontend_contract.py</file></read_first>
  <action>
    `test_periodic_summary_excludes_hidden_and_uses_loaded_messages`:
    `.filter(e=>!deleted.has(e.id)` → `.filter(e=>!App.state.deleted.has(e.id)`.
    `test_ai_summary_is_explicit_and_warns_before_remote_transmission`:
    `` fetch(`${API}/api/ai-summary` `` → `` fetch(`${App.api}/api/ai-summary` ``.
    `test_frontend_assets_are_externalized_without_build_tooling`: añadir
    `assert '<script src="/static/shared.js"></script>' in html` y comprobar
    orden shared.js < app.js < summary.js.
    Comentar en cada aserción modificada que la intención se conserva.
  </action>
  <acceptance_criteria>
    <criterion>`pytest -q` verde (incluye `tests/test_server_api.py` por el nuevo estático)</criterion>
  </acceptance_criteria>
</task>

<task id="32-B5" name="Verificación Stage B" type="verify">
  <action>
    `python3 -m pytest -q` · `node --check` sobre shared.js, app.js, summary.js ·
    arrancar `server.py`, abrir la app, generar un Resumen operativo 7/30 días y
    comprobar que excluye ocultos y que el botón "Resumir con AI" avisa si el
    proveedor es remoto.
  </action>
  <acceptance_criteria>
    <criterion>Suite verde, sin fallos nuevos</criterion>
    <criterion>Resumen operativo funciona y respeta ocultos</criterion>
  </acceptance_criteria>
</task>

---

## Stage C — Espacio de nombres para estado compartido reasignado (riesgo medio · OPCIONAL)

`activeEmails`, `aiStatus` y `CATS` se **reasignan** en `app.js`, así que exponer
la referencia en `App` una sola vez no basta. Dos técnicas posibles; elegir una
en `32-DISCUSSION` antes de ejecutar:

- **C-a (repunte total):** cambiar todas las referencias a `App.state.activeEmails`
  / `App.state.aiStatus` / `App.config.CATS` en ambos archivos
  (~36 sitios app.js + ~7 summary.js). Máxima claridad, máximo diff.
- **C-b (accessor):** mantener los `let` locales en `app.js` y publicar getters:
  `Object.defineProperty(App.state,'activeEmails',{get:()=>activeEmails});` etc.
  `summary.js` usa `App.state.*`; `app.js` queda casi intacto. Menos diff, algo
  de "magia".

<task id="32-C1" name="Decidir técnica C-a vs C-b" type="discuss">
  <action>
    Registrar en `.planning/phases/32-encapsulacion-js/32-DISCUSSION-LOG.md` la
    técnica elegida y el motivo. Criterio sugerido: C-b si el objetivo es cerrar
    MNT-02 con el mínimo riesgo; C-a si se quiere dejar `app.js` preparado para
    una modularización futura.
  </action>
</task>

<task id="32-C2" name="Aplicar la técnica elegida a activeEmails / aiStatus / CATS" type="execute">
  <read_first>
    <file>static/app.js</file>
    <file>static/summary.js</file>
    <file>.planning/phases/32-encapsulacion-js/32-CONTEXT.md</file>
  </read_first>
  <action>
    Según C-a o C-b. Mantener `SEVERITY_META` y familia como están (no los usa
    summary.js directamente). Actualizar la cabecera SHARED SURFACE.
  </action>
  <acceptance_criteria>
    <criterion>`summary.js` no referencia `activeEmails`/`aiStatus`/`CATS` desnudos</criterion>
    <criterion>`node --check` OK en ambos</criterion>
  </acceptance_criteria>
</task>

<task id="32-C3" name="Contract test: aserciones de Stage C" type="execute">
  <action>
    `test_periodic_summary_excludes_hidden_and_uses_loaded_messages`:
    `'activeEmails' in APP_JS` → aserción equivalente sobre el acceso vía `App`.
    `test_open_message_state_survives_attachment_hydration_render` y
    `test_attachment_hydration_updates_source_message_and_finishes_on_error`:
    actualizar los fragmentos con `activeEmails` al nuevo acceso (solo si C-a;
    con C-b los `let` locales siguen y estas aserciones no cambian).
    Preservar la intención de cada una en un comentario.
  </action>
  <acceptance_criteria>
    <criterion>`pytest -q` verde</criterion>
  </acceptance_criteria>
</task>

<task id="32-C4" name="Smoke manual completo" type="verify">
  <action>
    Ejecutar el plan humano `TESTING_HUMANO.md` §2 (Búsqueda), §3 (Archivar /
    Etiquetar), §4 (Automatización), §5 (IA), §6 (Exportación + lector). Todos
    deben pasar sin regresión visible.
  </action>
  <acceptance_criteria>
    <criterion>Los 5 bloques del plan humano pasan</criterion>
  </acceptance_criteria>
</task>

---

## Cierre (tras las stages ejecutadas)

<task id="32-Z1" name="Actualizar documentación y ADR" type="execute">
  <action>
    `.planning/DECISIONS.md`: ADR-011 — "Espacio de nombres `App` para el estado
    compartido de front sin build tooling"; motivo, alcance (qué se movió y qué
    no), consecuencia sobre `test_frontend_contract.py`.
    `.planning/STATE.md`: marcar Fase 32; actualizar recuento de tests y
    "Last Activity" / "Next Recommended Action".
    `.planning/ROADMAP.md` y `.planning/REQUIREMENTS.md`: `MNT-02` → Done si se
    completó al menos Stage B (dependencias cruzadas del estado compartido
    resueltas); dejar nota si Stage C queda pendiente.
    `NOTEBOOK.md`: observación técnica sobre `App` y el orden de carga
    `shared.js → app.js → summary.js`.
  </action>
</task>

## Riesgos

- **Test de cadena literal frágil:** cada reubicación obliga a editar aserciones.
  Mitigación: cambiar solo las que nombran el símbolo movido, documentar la
  intención, no tocar las de comportamiento/UX/endpoint salvo el identificador.
- **`app.js` sin tests de runtime:** solo hay string-match + plan humano.
  Mitigación: Stage C gateado por smoke manual; Stage A/B casi no tocan el cuerpo.
- **Orden de carga:** `shared.js` debe cargar primero; si falla, `App` es
  `undefined` y rompe todo. Mitigación: `window.App=window.App||{...}` y test de
  orden de `<script>` en el contrato.
- **Regresión de plegado de paneles** (Stage A3). Mitigación: verificación
  explícita de los 4 paneles.

## Recomendación

Ejecutar **Stage A + Stage B** en esta fase (bajo riesgo, cierra la parte de
MNT-02 sobre *dependencias cruzadas* — que es lo que nombra el roadmap).
Tratar **Stage C** como trabajo opcional posterior, solo si se quiere dejar
`app.js` listo para una modularización mayor; requiere smoke manual completo y
aporta menos por unidad de riesgo.
