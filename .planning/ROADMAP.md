# Roadmap: Gestor de Correos — Servidor Local

## Milestone 1: Local Tool Hardening

Goal: convertir la app actual en una herramienta local segura, verificable y preparada para crecer.

### Phase 1 — Seguridad y Base Operativa

**Status:** Completed 2026-06-01.

**Outcome:** la app mantiene la funcionalidad actual, pero elimina los riesgos principales.

Scope:
- Cerrar o restringir CORS.
- Cambiar la UI a endpoints relativos.
- Añadir validación robusta de `sender` y `max`.
- Evitar que `/api/status` active OAuth.
- Endurecer escape/render de HTML dinámico.
- Documentar seguridad, secretos y ejecución.

Requirements: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, REL-01, ARCH-04.

Verification:
- `.venv/bin/python -m py_compile server.py`
- Prueba manual de `/api/status`.
- Prueba manual de búsqueda con remitente válido e inválido.
- Revisión de que `credentials.json` y `token.json` no quedan rastreables.

### Phase 2 — Modularización y Tests

**Status:** Completed 2026-06-01.

**Outcome:** la lógica crítica deja de vivir en un único archivo y pasa a ser testeable.

Scope:
- Extraer cliente Gmail a `gmail_client.py`.
- Extraer clasificación a `classifier.py`.
- Mantener `ThreadingHTTPServer` y cubrir comportamiento con pruebas de API.
- Añadir `pytest`.
- Crear tests para fechas, validación, clasificación y respuestas API.

Requirements: REL-03, ARCH-01, ARCH-02.

Verification:
- `pytest`
- `.venv/bin/python server.py`
- Pruebas manuales de UI sin regresiones.

### Phase 3 — Persistencia Local

**Status:** Completed 2026-06-01.

**Outcome:** la herramienta recuerda fuentes, ocultados y preferencias. Las reglas editables permanecen en v2.

Scope:
- Diseñar almacenamiento local SQLite o JSON.
- Persistir fuentes añadidas.
- Persistir correos ocultos y preferencias de filtros.
- Añadir migración inicial o bootstrap automático.

Requirements: ARCH-03, PROD-02.

Plan:
- `.planning/phases/03-persistencia-local/03-PLAN.md`

Summary:
- `.planning/phases/03-persistencia-local/03-SUMMARY.md`
- `.planning/phases/03-persistencia-local/03-VERIFICATION.md`

Follow-up:
- Añadido indicador accesible de adjuntos en cabecera y apertura de adjuntos vía Gmail readonly (`PROD-05`).
- La acción local ya se muestra como `Ocultar`, evitando la ambigüedad con acciones reales de Gmail.

Verification:
- Recargar navegador sin perder estado.
- Reiniciar servidor sin perder configuración.

### Phase 4 — Inteligencia Operativa

**Status:** Completed 2026-06-01.

**Outcome:** la herramienta deja de ser un listado y se convierte en panel de decisiones.

Scope:
- Vista de acciones pendientes.
- Severidad por reglas.
- Agrupación por incidente/proveedor/categoría.
- Exportación de informes Markdown/JSON limpios.

Requirements: PROD-01, PROD-03, PROD-04.

Verification:
- Correos críticos aparecen arriba con motivo.
- Exportación contiene resumen, fuente, fecha, categoría, severidad y enlace Gmail.

### Post-v1 Hardening

**Status:** Completed 2026-06-08.

- Rechazo explícito de cabeceras `Host` no locales y orígenes externos.
- Límite efectivo de resultados: `max` limita mensajes devueltos, no sólo hilos Gmail consultados.
- Escala tipográfica contextual aumentada, controles ampliados y adaptación responsive mejorada.
- Sincronización de documentación con la implementación y las verificaciones de Fase 4.

Requirement: UI-01.

## Milestone 2: Intelligence and Frontend Foundations

Goal: convertir la base local endurecida en un panel operativo configurable y mantener el frontend preparado para evolucionar.

### Phase 5 — Reglas Editables

**Status:** Completed 2026-06-08.

**Outcome:** el usuario puede crear y eliminar reglas locales que combinan proveedor y palabras clave para asignar categoría y severidad.

Scope:
- Persistir reglas personalizadas validadas en `app_state.json`.
- Aplicar reglas a mensajes Gmail normalizados y al pool local de la UI.
- Recalcular cola, filtros, motivos y exportaciones tras cambios.
- Mantener Gmail readonly y no guardar contenido de mensajes.

Requirement: INT-02.

Verification:
- `.venv/bin/python -m pytest`
- Validación de sintaxis Python y JavaScript.
- Smoke HTTP de `/api/state` y HTML servido.

### Phase 6 — Resúmenes Periódicos

**Status:** Completed 2026-06-09.

**Outcome:** el usuario puede generar un resumen operativo local de los últimos 7 o 30 días.

Scope:
- Contar severidades y destacar acciones prioritarias.
- Mostrar proveedores y categorías principales.
- Copiar o descargar el resumen en Markdown.
- Calcular únicamente sobre correos cargados y visibles, sin persistir contenido Gmail.

Requirement: INT-01.

Verification:
- `.venv/bin/python -m pytest`
- Validación de sintaxis JavaScript.
- Smoke HTTP del HTML servido.

### Phase 7 — Tendencias y Recurrencias

**Status:** Completed 2026-06-09.

**Outcome:** cada resumen compara períodos equivalentes y señala cambios operativos observables.

Scope:
- Comparar volumen total y severidad alta con el período anterior.
- Detectar aumentos por proveedor y categoría.
- Identificar asuntos recurrentes normalizando respuestas, fechas y números.
- Incluir tendencias en la vista y exportación Markdown sin persistir contenido Gmail.

Requirement: INT-03.

Verification:
- `.venv/bin/python -m pytest`
- Validación de sintaxis JavaScript.
- Smoke HTTP del HTML servido.

### Phase 8 — Resumen AI Opcional

**Status:** Completed 2026-06-09.

**Outcome:** el usuario puede solicitar explícitamente un resumen AI del informe operativo.

Scope:
- Mantener la integración desactivada si no hay proveedor configurado.
- Soportar endpoints compatibles con OpenAI mediante variables de entorno.
- Mantener la API key exclusivamente en el backend.
- Pedir confirmación antes de enviar el resumen a un proveedor remoto.

Requirement: INT-04.

Verification:
- `.venv/bin/python -m pytest`
- Respuesta controlada cuando AI no está configurada.
- Validación de sintaxis Python y JavaScript.

### Phase 9 — Modularización Frontend

**Status:** Completed 2026-06-09.

**Outcome:** la interfaz deja de concentrar estructura, estilos y todo el comportamiento en un único HTML.

Scope:
- Extraer estilos a `static/app.css`.
- Extraer comportamiento principal a `static/app.js`.
- Separar resúmenes, tendencias y AI en `static/summary.js`.
- Servir una lista cerrada de activos locales sin introducir build tooling.

Requirement: ARCH-05.

Verification:
- `.venv/bin/python -m pytest`
- Validación de sintaxis de ambos archivos JavaScript.
- Smoke HTTP de HTML, CSS y JavaScript servidos.

### Post-v2 Responsive Hardening

**Status:** Completed 2026-06-09.

- Contención horizontal de campos y controles en grids.
- Botón de reglas en fila propia y adaptación a una columna en móvil.
- Barras de acciones, avisos y controles de modal con envoltura o apilado responsive.

Requirement: UI-02.

### Post-v2 Reliability Hardening

**Status:** Completed 2026-06-09.

- Las desconexiones o cancelaciones del navegador durante una respuesta HTTP se tratan como cierre normal del cliente.
- Las respuestas JSON, activos estáticos y adjuntos comparten el mismo manejo de escritura interrumpida.
- El estado de apertura de correos sobrevive a los re-renderizados provocados por la carga de adjuntos.
- La hidratación de adjuntos actualiza el correo fuente real y siempre termina en estado comprobado o error visible.

## Later

- Unificar o generar desde una fuente común las reglas base duplicadas entre backend y frontend.
- Escritura Gmail adicional mediante labels o archivado, fuera del milestone v3.
- Mantener la semántica de `Ocultar` sólo para la vista local; cualquier acción sobre Gmail debe tener nombre y contrato propios.

## Milestone 3: Hidden Lifecycle and Permanent Deletion

Goal: convertir los ocultos locales en una cola revisable y permitir su borrado permanente mediante una frontera Gmail destructiva explícita.

### Phase 10 — Bandeja de Ocultos

**Status:** Completed 2026-06-10.

**Outcome:** el usuario puede revisar todos los ocultos y decidir cuáles restaurar o conservar ocultos.

Scope:
- Añadir una bandeja/modal dedicado a ocultos con selección individual y masiva.
- Resolver por ID los mensajes ocultos que no estén cargados en memoria.
- Restaurar seleccionados como visibles sin modificar Gmail.
- Identificar mensajes no localizables o ya eliminados.

Requirements: HID-01, HID-02, HID-03, HID-04.

Verification:
- Pruebas de contrato frontend para selección, restauración y estados no disponibles.
- Pruebas API para resolución segura de IDs ocultos.
- Verificación manual sin ampliar scopes Gmail.

### Phase 11 — Frontera de Autorización Destructiva

**Status:** Completed 2026-06-10.

**Outcome:** el permiso completo de Gmail queda aislado del cliente readonly y sólo se activa de forma explícita.

Scope:
- Mantener `token.json` y operaciones normales con `gmail.readonly`.
- Añadir un token destructivo privado separado para `https://mail.google.com/`.
- Desactivar la capacidad mediante configuración local por defecto.
- Exponer estado pasivo de disponibilidad sin iniciar OAuth.

Requirements: AUTH-01, AUTH-02, AUTH-03, AUTH-04.

Verification:
- El arranque y lectura normal siguen funcionando sin token destructivo.
- La autorización destructiva sólo comienza tras acción explícita.
- Tokens y configuración destructiva permanecen fuera de Git y con permisos privados.

### Phase 12 — API de Borrado Permanente

**Status:** Completed 2026-06-10.

**Outcome:** el backend puede borrar de forma irreversible un lote acotado de mensajes ocultos y devolver resultados por mensaje.

Scope:
- Implementar `users.messages.delete` sólo para IDs presentes en `hidden_ids`.
- Validar frase de confirmación exacta y limitar lotes a 20 IDs únicos.
- Serializar operaciones Gmail destructivas y devolver éxitos/fallos individuales.
- No borrar ni modificar mensajes visibles mediante este endpoint.

Requirements: DEL-01, DEL-02, DEL-03.

Verification:
- Tests con Gmail simulado; ninguna prueba automatizada borra correo real.
- Rechazo de IDs visibles, lotes excesivos y confirmaciones incorrectas.
- Prueba real manual únicamente con un mensaje de prueba prescindible.

### Phase 13 — Flujo Destructivo y Auditoría Local

**Status:** Completed 2026-06-10.

**Outcome:** la bandeja de ocultos permite ejecutar el borrado permanente con advertencias inequívocas y registrar su resultado mínimo.

Scope:
- Añadir acción separada `Eliminar permanentemente de Gmail`.
- Exigir confirmación escrita con cantidad exacta y advertencia irreversible.
- Mostrar progreso y resultados parciales sin reintento automático.
- Retirar éxitos de ocultos y guardar auditoría local acotada: ID, fecha y resultado, sin contenido Gmail.

Requirements: DEL-04, DEL-05.

Verification:
- Pruebas de contrato UI y persistencia de auditoría.
- Flujo manual de cancelación sin efectos.
- Flujo real controlado con un único mensaje de prueba y comprobación posterior en Gmail.

## Milestone 4: Persistent Hidden Authorization and Bulk Deletion

Goal: reutilizar la autorización destructiva válida entre sesiones y ampliar de forma segura los lotes de borrado de ocultos sin salir del contrato hidden-only.

### Phase 14 — Persisted Destructive Authorization

**Status:** Completed 2026-06-10.

**Outcome:** el token destructivo válido se reusa entre sesiones y la interfaz informa con claridad cuándo sigue siendo válido o necesita reautorización.

Scope:
- Reusar `delete_token.json` automáticamente mientras siga siendo válido.
- Mantener la frontera destructiva aislada del flujo readonly normal.
- Exponer en `/api/status` y en la UI si la autorización destructiva está ausente, válida, caducada o revocada.
- Evitar la reautorización automática al arrancar la app.

Requirements: AUTH-05, AUTH-06.

Verification:
- Reiniciar la app y comprobar que el token válido sigue funcionando sin repetir OAuth.
- Forzar un token caducado o revocado y comprobar que exige reautorización.
- Confirmar que Gmail readonly sigue operativo sin tocar el token destructivo.

### Phase 15 — Bulk Hidden Deletion

**Status:** Completed 2026-06-10.

**Outcome:** el usuario puede borrar lotes grandes de correos ocultos desde la cola paginada sin romper la trazabilidad ni la confirmación reforzada.

Scope:
- Permitir construir lotes grandes desde páginas y rangos de ocultos ya paginados.
- Elevar el máximo de borrado a 100 IDs ocultos por solicitud.
- Procesar Gmail en tandas acotadas internamente para evitar llamadas desbordadas.
- Mantener resultados por ID y auditoría local mínima para lotes grandes.
- Conservar la confirmación exacta ligada al tamaño total de la selección.

Requirements: HID-05, DEL-06, DEL-07, DEL-08.

Verification:
- Pruebas de contrato para selección paginada y estado del lote en UI.
- Pruebas API para chunking interno y resultados por ID.
- Smoke manual con mensajes prescindibles únicamente.

## Milestone 5: Destructive Revocation, Orphan Cleanup, and Operational Clarity

Goal: dar una salida explícita al scope destructivo, refinar la limpieza local de huérfanos y hacer más clara la operativa de mantenimiento sin ampliar escrituras Gmail.

### Phase 16 — Destructive Revocation

**Status:** Completed 2026-06-11.

**Outcome:** el usuario puede revocar el token destructivo explícitamente y la UI refleja el estado resultante sin ambigüedad.

Scope:
- Añadir revocación explícita de `delete_token.json` desde UI y API.
- Mantener el resto del estado local intacto al revocar.
- Reflejar en `/api/status` y en la UI si el token está revocado, ausente o disponible.
- Evitar reautorizaciones implícitas durante el arranque.

Requirements: AUTH-07, AUTH-08.

Verification:
- Revocar token y comprobar que se borra el acceso destructivo sin afectar otras preferencias.
- Verificar que el estado de la API cambia a revocado/ausente correctamente.
- Confirmar que Gmail readonly sigue operativo.

### Phase 17 — Orphan Cleanup Refinement

**Status:** Completed 2026-06-11.

**Outcome:** los huérfanos se distinguen y limpian con más precisión en la cola local sin confundirse con mensajes operables.

Scope:
- Diferenciar mejor mensajes disponibles, no localizables y ya desconectados de Gmail.
- Añadir limpieza local controlada para huérfanos sin tocar Gmail.
- Reducir ruido visual y de selección al revisar ocultos desfasados.

Requirements: HID-06, HID-07, HID-08.

Verification:
- Tests de contrato para estados de huérfanos.
- Flujo manual de limpieza local sin efectos en Gmail.
- Comprobación de que la revisión de ocultos sigue funcionando.

### Phase 18 — Operational Clarity

**Status:** Completed 2026-06-11.

**Outcome:** la interfaz de mantenimiento deja claro qué acción afecta a Gmail y cuál sólo al estado local.

Scope:
- Separar visualmente acciones destructivas, de mantenimiento local y de revisión.
- Reducir carga mental en el modal y en los flujos de limpieza.
- Mejorar copy, jerarquía y feedback para evitar dudas operativas.

Requirements: UI-03, UI-04.

Verification:
- Pruebas de contrato de UI.
- Revisión visual de los flujos de mantenimiento.
- Smoke manual con una selección pequeña de mensajes prescindibles.

### Post-v5 Reliability Follow-up

**Status:** Completed 2026-06-11.

- Clasificación diferenciada entre huérfanos Gmail y fallos temporales.
- Purga automática de referencias huérfanas y de su copia cargada en la sesión.
- Guardado inmediato antes de recargar la bandeja para evitar referencias fantasma.
- Logo y favicon locales servidos desde la allowlist de activos.
- Retirada del pool estático `BASE`; las fuentes fijas y personalizadas se cargan desde Gmail.
- Reglas personalizadas ampliadas con coincidencia de alguna o todas las palabras clave.

## Product Backlog — Refinements & Future Features

## Milestone 6: Remote Deployment and Full Export

Goal: habilitar la operación remota segura y la extracción de contenidos íntegros sin persistencia local.

### Phase 19 — Full Message Content Export

**Status:** Completed 2026-06-12.

**Outcome:** el usuario puede exportar el contenido completo de los correos en formato .eml o .zip.

Scope:
- Obtención de cuerpo RFC822 vía Gmail `format=raw`.
- Descarga individual (.eml) o por lotes (.zip).
- Sin persistencia de contenidos en el servidor local.

### Phase 20 — Private VPN Remote Deployment

**Status:** Completed 2026-06-12.

**Outcome:** la aplicación puede ejecutarse como servicio remoto seguro a través de una VPN.

Scope:
- Configuración por variables de entorno (HOST, PORT, HEADLESS).
- Soporte para orígenes personalizados (CORS) y carga de `.env`.
- Documentación de despliegue y flujo OAuth sin navegador.

## Milestone 7: Gmail Management and Automation

Goal: transformar la app en una herramienta de gestión bidireccional con Gmail, permitiendo organizar el buzón real mediante reglas e IA.

### Phase 21-23 — Refinamiento de Búsqueda y Reglas

**Status:** Completed 2026-06-12.

**Outcome:** búsqueda avanzada integrada y lógica unificada.

Scope:
- Buscador integrado en el modal de ocultos.
- Unificación de categorías y severidades en el backend (`classifier.py`).
- Búsqueda avanzada por fechas y texto literal nativo de Gmail.

### Phase 24-25 — Gestión de Gmail (Archive & Labels)

**Status:** Completed 2026-06-12.

**Outcome:** el usuario puede organizar su cuenta de Gmail directamente desde la app.

Scope:
- Elevación de scope a `gmail.modify`.
- Acción de archivado real (retirar INBOX) con ocultado local automático.
- Gestión de etiquetas: listar, aplicar y crear etiquetas dinámicamente.

### Phase 26-29 — Automatización, IA e Integración Local

**Status:** Completed 2026-06-12.

**Outcome:** reglas proactivas, sugerencias inteligentes e integración profunda con el SO.

Scope:
- Auto-etiquetado y Auto-archivado vinculado a reglas personalizadas.
- Sugerencias AI de reglas basadas en acciones locales (opcional).
- Directorio de exportación persistente (`/exports`) sin descargas de navegador.
- Lector EML integrado en la app (sin dependencias externas).
- Integración con macOS Services ("Acciones rápidas").

## Milestone 8: Refinamiento UX y Mantenimiento

Goal: pulir la experiencia de uso y saldar deuda técnica sin ampliar la
superficie funcional ni la de escritura en Gmail. Estado canónico en
`.planning/STATE.md`.

### Phase 30 — Refactor UX v8

**Status:** Completed 2026-06-16 (`e504f4c`, `b6679f3`).

**Outcome:** la vista de un correo se abre en un modal dedicado (subventana),
las categorías del panel lateral son reactivas y el estado de IA es reseteable.

Scope:
- Sustituir la tarjeta expandible inline por un modal con hidratación de
  adjuntos bajo demanda (`openEmailModal`).
- Categorías reactivas al aplicar/editar reglas y filtros.
- Reset del estado de IA y mejoras de filtros, scroll y modal.

Requirements: UX-01, UX-02.

### Phase 31 — Suite Verde

**Status:** Completed 2026-09-08.

**Outcome:** `pytest` 129/129 verde. Los 3 tests obsoletos se reescribieron al
contrato vigente (exportación a `EXPORTS_DIR` + JSON; modal de correo con
re-render tras hidratar adjuntos). Sin cambios de comportamiento en `server.py`
ni `static/app.js`.

Scope:
- Actualizar `test_handle_messages_export_single_eml` y `..._zip` al contrato
  actual (escritura en `/exports`, respuesta JSON).
- Actualizar `test_open_message_state_survives_attachment_hydration_render` al
  modelo de modal, o sustituirlo por una aserción del contrato vigente.
- Sin cambios de comportamiento en `server.py` ni `static/app.js`.

Requirement: MNT-01.

Verification: `.venv/bin/python -m pytest` sin fallos.

### Phase 32 — Encapsulación JS

**Status:** Stage A + B completados 2026-09-08. Stage C opcional, pendiente.
Plan: `.planning/phases/32-encapsulacion-js/32-PLAN.md` (contexto: `32-CONTEXT.md`).

**Outcome:** la superficie compartida `app.js → summary.js` empieza a pasar por
un espacio de nombres `App` explícito (`static/shared.js`), sin build tooling.

Entregado (Stage A + B):
- `summaryDays`/`summaryData` reubicados en `summary.js` (estado que solo usa él).
- Cabecera SHARED SURFACE en `app.js` y `summary.js`.
- `index.html` sin `onclick` inline: paneles plegables cableados por JS.
- `static/shared.js` (nuevo, registrado en `STATIC_FILES`, cargado primero)
  define `window.App`. `app.js` publica `App.api` y `App.state.deleted`;
  `summary.js` los consume vía `App.*` (0 globales desnudas de esos dos).
- `test_frontend_contract.py`: 3 aserciones actualizadas al acceso vía `App`
  (intención preservada) + `test_shared_namespace_is_declared_and_documented`.

Pendiente (Stage C, opcional): `activeEmails`, `aiStatus`, `CATS` — se reasignan
en `app.js` (~36 sitios); requiere smoke manual del plan humano §2–§6.

Requirement: MNT-02. Decisión: ADR-011.

Verification: `pytest` (136/136) · `node --check` (shared.js, app.js, summary.js) ·
smoke de servido estático y orden de `<script>`.

### Phase 33 — Rendimiento de Lotes

**Status:** Completed 2026-09-08.

**Outcome:** archivado y etiquetado de lotes grandes troceados internamente y
acotados; la UI avisa antes de lotes grandes.

Hallazgo: el borrado permanente ya troceaba (`DELETE_EXECUTION_CHUNK = 20`),
pero `archive_messages` y `apply_label` enviaban **todos** los IDs en una sola
llamada a `batchModify` (límite duro de Gmail: 1000 IDs/petición), sin cota ni
troceado.

Scope entregado:
- `gmail_client._batch_modify_chunked`: tandas de `BATCH_MODIFY_CHUNK = 100` bajo
  `_api_lock`, devuelve `{'total','chunks'}`. `archive_messages` y `apply_label`
  pasan a usarlo.
- Handlers `/api/messages/archive` y `/api/messages/label`: rechazan lotes
  > `MAX_BATCH_MODIFY = 1000` y devuelven `chunks` en la respuesta.
- `static/app.js`: `guardBatchSize()` — corta en >1000 y pide confirmación en
  >200; el texto del botón indica el volumen.
- +6 tests (troceado, cota de lote, ocultado local).

Requirement: MNT-03. Decisión: ADR-010.

Verification: `.venv/bin/python -m pytest` (135/135) · `py_compile` · `node --check static/app.js`.

## Milestone 9: App macOS nativa

Goal: distribuir la herramienta como una `.app` de macOS con ventana propia, sin
romper la app web ni la CLI. Rama: `feat/macos-app`.
Plan: `.planning/phases/34-app-macos/34-PLAN.md`. Decisión: ADR-012.

### Phase 34 — App macOS (Developer ID + notarización)

**Status:** Completed 2026-09-09.

**Outcome:** `.app` con WKWebView (`pywebview`) que arranca/detiene `server.py`,
empaquetada con py2app, firmada (Developer ID Application), Hardened Runtime,
notarizada y *stapled*, distribuida en DMG (`dist/GestorDeCorreos.dmg`). La app
web y la CLI no cambian. Verificado en el Mac del usuario: ventana + login Gmail
OK; `codesign -dv` → `flags=runtime`, Developer ID `V29BTBRY6G`, timestamp.

Scope entregado:
- `paths.py`: carpeta de datos escribible (proyecto desde fuente,
  `~/Library/Application Support/GestorDeCorreos/` en el `.app`) y carpeta de
  recursos de solo lectura. `gmail_client`/`destructive_gmail`/`storage`/`server`
  toman sus rutas de ahí, manteniendo nombres de constante y tests. +7 tests.
- `macos/`: `app_main.py` (pywebview, puerto libre efímero), `setup.py` (py2app),
  `entitlements.plist`, `build_app.sh`, `README.md`. `requirements-macos.txt`.

Hallazgos del build real (fijados en `build_app.sh` y `setup.py`):
- Homebrew Python no vale para py2app: hace falta **framework build** (python.org)
  → `PYTHON=/usr/local/bin/python3.12`.
- `google` es namespace package: crea `__init__.py` en el build-venv y va en
  `packages` para no acabar dentro de `python3XX.zip` (un `.so` en un zip no se
  puede firmar).
- `codesign --deep` no firma los binarios anidados → notarización *Invalid*.
  Firma **inside-out**: cada `.so`/`.dylib`/framework con `--options runtime
  --timestamp`, el bundle al final con entitlements.

Requisitos: MAC-01 … MAC-05 (todos Done).

Verification: `pytest` (143/143) · DMG notarizado + `stapler validate` OK ·
`spctl` accepted en el Mac.

### Phase 35 — Mac App Store (futuro)

**Status:** Not started. Rama y milestone aparte.

Shell nativo Swift/SwiftUI + WKWebView, App Sandbox, `server.py` como helper
bundled o port parcial a Swift, cert *3rd Party Mac Developer*, App Review.

## Product Backlog — Future Features

- **Soporte Multi-cuenta:** Permitir gestionar varios perfiles de Gmail desde la misma instancia.
- **Histórico de Auditoría Extendido:** Trazabilidad completa de acciones AI y archivados masivos.
- **Análisis de Adjuntos:** Búsqueda y filtrado avanzado por tipo/tamaño de archivo adjunto.
- **Sincronización AI automática:** aplicar sugerencias de IA como "reglas temporales" para limpiezas puntuales.
