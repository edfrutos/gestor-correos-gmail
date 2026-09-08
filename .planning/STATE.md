---
gsd_state_version: 1.0
milestone: v9
milestone_name: App macOS nativa
status: in_progress
last_updated: "2026-09-08T00:00:00.000Z"
branch: feat/macos-app
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 1
  completed_plans: 0
  percent: 60
---

# State — Fuente única de estado

> Este archivo es la **referencia canónica** del estado del proyecto.
> El resto de documentos (`README.md`, `NOTEBOOK.md`, `FEEDBACK.md`,
> `REQUIREMENTS.md`, `ROADMAP.md`) deben remitir aquí en vez de repetir cifras.

## Project Reference

See: `.planning/PROJECT.md` · `.planning/ROADMAP.md` · `.planning/REQUIREMENTS.md`

**Core value:** Detectar y priorizar correos técnicos importantes sin exponer
datos de Gmail fuera del equipo local o de una VPN privada.

**Current focus:** Milestone v9 — empaquetar la herramienta como `.app` de macOS
(ventana WKWebView, Developer ID + notarización) **sin romper la app web ni la
CLI**. Rama `feat/macos-app`. Milestone v8 (refinamiento) cerrado y commiteado
en `main` (`ac46a72`/`d2fb240`/`b34c42d`).

## Current Status

- **Funcionalidad:** madura. Milestones v1 → v7.5 completados (Fases 1–29);
  v8 (refinamiento) completado en `main`.
- **v9 en curso (rama `feat/macos-app`):** `paths.py` + relocalización de estado
  escribible a `data_dir()` hechos y con tests; andamiaje `macos/` (pywebview,
  py2app, firma, notarización, DMG) escrito. Build real pendiente en el Mac.
- **Scope Gmail:** `gmail.modify` para lectura/archivado/etiquetado;
  borrado permanente aislado en `delete_token.json` (`https://mail.google.com/`),
  desactivado por defecto.
- **Suite automatizada:** `143 tests` · **143 verdes** (v9 añadió `test_paths.py`,
  +7; el rewiring de rutas no cambió ningún test existente).
- **Testeo humano:** `TESTING_HUMANO.md` 30/30 ✅ (v7.5).

## Milestone v9 — Fases (rama `feat/macos-app`)

| Fase | Descripción | Estado |
|------|-------------|--------|
| 34 — App macOS (Developer ID) | `paths.py` + relocalización de estado; `macos/` (pywebview, py2app, entitlements, `build_app.sh`), docs | 🟡 Andamiaje + tests hechos en Linux; **build/firma/notarización pendientes en el Mac** |
| 35 — Mac App Store | Shell nativo Swift + WKWebView, App Sandbox, App Review | ⬜ Futuro, rama aparte |

## Milestone v8 — Fases (cerrado en `main`)

| Fase | Descripción | Estado |
|------|-------------|--------|
| 30 — Refactor UX v8 | Categorías reactivas, subventana (modal) de correos, reset de IA, filtros/scroll/modal | ✅ Done (`e504f4c`, `b6679f3`) |
| 31 — Suite verde | Sanear los 3 tests obsoletos contra el contrato vigente; suite 129/129 verde | ✅ Done (2026-09-08) |
| 33 — Rendimiento de lotes | Troceado interno de archivado/etiquetado (`BATCH_MODIFY_CHUNK=100`), cota de lote (`MAX_BATCH_MODIFY=1000`) y aviso en UI para lotes >200 | ✅ Done (2026-09-08) |
| 32 — Encapsulación JS | Stage A (relocación `summaryDays`/`summaryData`, cabecera SHARED SURFACE, sin `onclick` inline) + Stage B (`static/shared.js` con `App`; `API`/`deleted` compartidos vía `App.*`) | ✅ Done (2026-09-08). Stage C (`activeEmails`/`aiStatus`/`CATS`) opcional, pendiente |

## Known Issues

Ninguno abierto. La Fase 31 (2026-09-08) saneó los 3 tests que fallaban por
**assertions obsoletas** contra diseños superados (no eran regresiones):

1. `test_handle_messages_export_single_eml` / `..._zip` — reescritos al contrato
   de la Fase 29 / ADR-009 (escritura en `EXPORTS_DIR`, respuesta JSON), con
   `EXPORTS_DIR` monkeypatch a `tmp_path`.
2. `test_open_message_state_survives_attachment_hydration_render` — reescrito al
   modelo de modal de la Fase 30 / ADR-008 (`openEmailModal` + re-render del
   modal tras `hydrateMessageAttachments`).

## Known Risks

- `credentials.json`, `token.json`, `delete_token.json` y `app_state.json`
  deben permanecer fuera de Git (permisos `600`, ya en `.gitignore`).
- `gmail.modify` permite escritura (archivar/etiquetar); el borrado permanente
  mantiene su frontera destructiva adicional.
- Las sugerencias/resúmenes de IA envían metadatos (asunto/remitente) a un
  proveedor externo solo si el usuario lo habilita y confirma.
- `static/*.js` comparte estado mediante variables globales; refactor a encapsular
  con cuidado para no romper el contrato del frontend (`test_frontend_contract.py`).

## Last Activity

- 2026-09-08 — v9 arrancado en `feat/macos-app`: `paths.py` (carpeta de datos
  escribible vs. recursos de solo lectura) + rewiring de `gmail_client`,
  `destructive_gmail`, `storage`, `server` sin cambiar tests; andamiaje `macos/`
  (`app_main.py` pywebview, `setup.py` py2app, `entitlements.plist`,
  `build_app.sh`, `README.md`), `requirements-macos.txt`. Suite 143/143.
- 2026-09-08 — Milestone v8 cerrado en `main` (`ac46a72`/`d2fb240`/`b34c42d`):
  consolidación de docs + Fases 31–33 + Fase 32 A/B; `.env` fuera de git.
- 2026-09-08 — Fase 32 (Stage A+B): `static/shared.js` define `window.App`;
  `API` y `deleted` se comparten vía `App.*`; `summaryDays`/`summaryData`
  reubicados en `summary.js`; `onclick` inline retirados de `index.html`.
  +1 test. Ver ADR-011. Stage C (`activeEmails`/`aiStatus`/`CATS`) opcional.
- 2026-09-08 — Fase 33: `archive_messages`/`apply_label` trocean en tandas de 100
  (Gmail limita `batchModify` a 1000/petición); handlers rechazan lotes >1000;
  la UI avisa y trocea el texto para lotes >200. +6 tests. Ver ADR-010.
- 2026-09-08 — Consolidación de documentación (STATE.md como fuente única) y
  Fase 31: suite automatizada 129/129 verde (saneo de 3 tests obsoletos).
- 2026-06-16 — Fase 30: refactor UX v8 (categorías reactivas, modal de correos,
  reset de IA, mejoras de filtros/scroll/modal).
- 2026-06-14 — Sync de documentación v7.5+ (`README.md`, `.env.example`,
  `docs/VPN_DEPLOYMENT.md`) y testeo humano 30/30.
- 2026-06-12 — Fases 19–29: exportación `.eml`/`.zip`, despliegue VPN, búsqueda
  avanzada, gestión Gmail (archivar/etiquetar), automatización, sugerencias IA,
  lector EML integrado e integración con Servicios de macOS.
- 2026-06-11 — Milestone v5.0 completado.

## Next Recommended Action

**Fase 34 — build real en el Mac** (no se puede hacer en el entorno Linux actual):

1. `git checkout feat/macos-app` en el Mac.
2. `python3 -m pip install -r requirements.txt -r requirements-macos.txt`
3. Prueba sin empaquetar: `python3 macos/app_main.py` → debe abrir la ventana con
   la UI y arrancar/parar el servidor. Ajustar `macos/setup.py`
   (`includes`/`packages`) si `py2app` se queja de algún módulo.
4. `export DEV_ID_APP=... AC_PROFILE=... && bash macos/build_app.sh` → DMG firmado
   y notarizado en `dist/`.
5. Verificar con `spctl` / `stapler validate` en otro Mac.
6. Reportar aquí ajustes necesarios para fijar `34-PLAN.md` y cerrar la fase.

Pendientes menores: AppleEvent `odoc` para abrir `.eml` con la app ya abierta;
Fase 32 Stage C (opcional); Fase 35 (Mac App Store, rama aparte).
