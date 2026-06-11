---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Destructive Revocation, Orphan Cleanup, and Operational Clarity
status: complete
last_updated: "2026-06-11T00:00:00Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 3
  completed_plans: 3
  percent: 100
---

# State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-06-11)

**Core value:** Detectar y priorizar correos técnicos importantes sin exponer datos de Gmail fuera del equipo local.  
**Current focus:** milestone v5.0 completado; revocación explícita del token destructivo, limpieza local de huérfanos y claridad operativa ya están cerradas

## Current Status

v1, v2, v3.0, v4.0 y v5.0 están implementadas. El último cierre de v5 separó visualmente las acciones locales de las acciones destructivas de Gmail.

## Last Activity

2026-06-11 — Retirado el pool estático `BASE`; las fuentes fijas y personalizadas se cargan desde Gmail y los huérfanos purgados ya no reaparecen tras recargar. Añadido operador `alguna`/`todas` a reglas personalizadas.
2026-06-11 — Sincronizada la documentación viva con v5 completado, API destructiva actual, lote máximo de 100, revocación, huérfanos y logo.
2026-06-11 — Añadidos logo SVG y favicon propios para la app, integrados en la cabecera y servidos desde la allowlist local de activos.
2026-06-11 — La purga de huérfanos ahora guarda el estado de inmediato antes de recargar la bandeja, evitando que queden referencias fantasma hasta una segunda interacción.
2026-06-11 — Los huérfanos detectados en la bandeja de ocultos se purgan ahora automáticamente de la app, eliminando también su copia cargada y su referencia local guardada.
2026-06-11 — Corregida la clasificación de huérfanos reales en la bandeja de ocultos: los mensajes con `Requested entity was not found` vuelven a etiquetarse como `orphan`, y la acción de limpieza local ya se activa sobre esos casos.
2026-06-11 — Completada Phase 18 de v5.0: separación visual de acciones locales y acciones que afectan a Gmail, con copy y jerarquía más claros en el modal de ocultos.
2026-06-11 — Completada Phase 16 de v5.0: revocación explícita del token destructivo desde UI/API, con estado `revoked` persistente y sin afectar al resto del estado local.
2026-06-11 — Completada Phase 17 de v5.0: limpieza local de huérfanos refinada, distinguiendo mensajes disponibles, huérfanos y fallos temporales sin tocar Gmail.
2026-06-11 — Iniciado milestone v5.0 `Destructive Revocation, Orphan Cleanup, and Operational Clarity`: revocación explícita del token destructivo, afinado de la limpieza local de huérfanos y mejora del flujo operativo.
2026-06-10 — Completado milestone v4.0 `Persistent Hidden Authorization and Bulk Deletion`: autorización destructiva persistente/recuperable entre sesiones y lote máximo de 100 ocultos con paginación separada; 117 pytest tests passing.
2026-06-10 — Iniciado milestone v4.0 `Persistent Hidden Authorization and Bulk Deletion`: persistencia de autorización destructiva válida y ampliación segura de lotes de ocultos.
2026-06-10 — Completado milestone v3.0: bandeja de ocultos, autorización destructiva separada, borrado permanente limitado y auditoría local; 114 pytest tests passing y ninguna prueba automatizada borró correo real.
2026-06-10 — Iniciado milestone v3.0 `Hidden Lifecycle and Permanent Deletion`: bandeja de ocultos, autorización destructiva aislada, API irreversible y auditoría local.
2026-06-10 — Corregida la comprobación infinita de adjuntos: la hidratación actualiza el correo fuente real, propaga IDs repetidos y muestra estado final también ante errores; 99 pytest tests passing.
2026-06-09 — Corregido el auto-cierre de correos tras hidratar adjuntos: el estado de apertura sobrevive a los re-renderizados del frontend; 98 pytest tests passing.
2026-06-09 — Las cancelaciones/desconexiones del navegador dejan de generar tracebacks `BrokenPipeError` o `ConnectionResetError` durante respuestas HTTP; 97 pytest tests passing.
2026-06-09 — Sincronizada la documentación viva con el estado real: v2 foundation completada, sin fase activa y siguiente objetivo pendiente de selección; 94 pytest tests passing.
2026-06-09 — Completado `UI-02`: corregido el desborde horizontal de reglas, barras de acciones, avisos y modales; 94 pytest tests passing.
2026-06-09 — Modularizado frontend en estructura, estilos, aplicación principal y módulo de resúmenes/tendencias/AI; 93 pytest tests passing.
2026-06-09 — Completada `INT-04`: resumen AI opcional mediante endpoint compatible con OpenAI, desactivado por defecto y con confirmación para proveedores remotos; 91 pytest tests passing.
2026-06-09 — Completada `INT-03`: comparación entre períodos equivalentes, aumentos por proveedor/categoría y asuntos recurrentes; 85 pytest tests passing.
2026-06-09 — Completada `INT-01`: resúmenes periódicos locales de 7/30 días con severidades, proveedores, categorías, acciones prioritarias y exportación Markdown; 84 pytest tests passing.
2026-06-09 — Inicializado repositorio Git local con secretos, estado privado, cachés y graphify excluidos.
2026-06-09 — Serializadas operaciones Gmail sobre el cliente compartido para evitar fallos SSL concurrentes; 82 pytest tests passing.
2026-06-08 — Completada `INT-02`: reglas editables locales con proveedor/palabras clave, categoría y severidad; 77 pytest tests passing.
2026-06-08 — Completada `UI-01`: nueva escala tipográfica contextual, controles ampliados y responsive ajustado.
2026-06-08 — Registrada como pendiente v2 la revisión integral de escala tipográfica y legibilidad contextual.
2026-06-08 — Añadida recuperación automática de tokens OAuth revocados y errores JSON controlados durante reautorización.
2026-06-08 — Sincronizada la documentación con v1 completada; endurecidos `Host`/`Origin`, límite real de resultados y permisos de archivos privados.
2026-06-01 — Completed Phase 4 intelligence operativa; 61 pytest tests passing.
2026-06-01 — Renamed the local hide action to `Ocultar` and updated docs/roadmap to remove Gmail-delete ambiguity.
2026-06-01 — Captured Phase 4 discussion context for bandeja de pendientes, severidad, agrupación y exportación.
2026-06-01 — Implemented attachment indicator in email header and readonly `/api/attachment` opening for Gmail attachments.
2026-06-01 — Completed Phase 3 persistence; 41 pytest tests passing and HTTP smoke tests passed.
2026-06-01 — Planned Phase 3 with `03-RESEARCH.md`, `03-PATTERNS.md`, and `03-PLAN.md`.
2026-06-01 — Captured attachment requirement as `PROD-05` in Phase 4: accessible header indicator and opening Gmail attachments without write actions.
2026-06-01 — Gathered Phase 3 discussion context and wrote `03-CONTEXT.md` / `03-DISCUSSION-LOG.md`.
2026-06-01 — Extracted Phase 2 learnings into `02-LEARNINGS.md`.
2026-06-01 — Completed Phase 2 modularization and tests; 31 pytest tests passing.
2026-06-01 — Extracted Phase 1 learnings into `01-LEARNINGS.md`.
2026-06-01 — Confirmed live Gmail sender search works after enabling Gmail API.
2026-06-01 — Exposed real Gmail API errors instead of silently returning empty search results; detected Gmail API disabled for Google Cloud project `app-catalogojoyero`.
2026-06-01 — Changed sender search semantics from "new import only" to "locate sender and expose matching messages for treatment".
2026-06-01 — Fixed sender import bug, installed Gmail dependencies in `.venv`, and restarted the local server with `.venv/bin/python server.py`.
2026-06-01 — Executed Phase 1 security hardening; added `01-SUMMARY.md` and `01-VERIFICATION.md`.
2026-05-31 — Added project credits: creator `EDF Developer`, user `edefrutos`.
2026-05-31 — Created GSD planning files, `NOTEBOOK.md`, `FEEDBACK.md`, `.gitignore`, and `requirements.txt`.

## Known Risks

- `credentials.json`, `token.json`, `delete_token.json` y `app_state.json` deben permanecer fuera de Git.
- El frontend conserva algunos `innerHTML` estructurales; los datos dinámicos principales continúan escapándose antes de insertarse.
- Las reglas base de categorías y severidad siguen duplicadas entre `classifier.py` y `static/app.js`; un cambio futuro debe mantenerlas sincronizadas o definir una fuente común.
- `https://mail.google.com/` es un scope restringido con capacidad de borrado permanente sobre todo el buzón; debe permanecer aislado, desactivado por defecto y fuera de las operaciones normales.
- Reusar autorización destructiva entre sesiones amplía la ventana operativa del scope destructivo; la revocación local debe seguir siendo clara y reversible.

## Next Recommended Action

Milestone v5.0 y seguimiento de fiabilidad completados. Siguiente prioridad pendiente de decisión de producto.
