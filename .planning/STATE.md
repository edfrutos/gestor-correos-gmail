---
gsd_state_version: 1.0
milestone: v10
milestone_name: Auto-actualización
status: in_progress
last_updated: "2026-09-09T00:00:00.000Z"
branch: feat/auto-update
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 85
---

# State — Fuente única de estado

> Este archivo es la **referencia canónica** del estado del proyecto.
> El resto de documentos (`README.md`, `NOTEBOOK.md`, `FEEDBACK.md`,
> `REQUIREMENTS.md`, `ROADMAP.md`) deben remitir aquí en vez de repetir cifras.

## Project Reference

See: `.planning/PROJECT.md` · `.planning/ROADMAP.md` · `.planning/REQUIREMENTS.md`

**Core value:** Detectar y priorizar correos técnicos importantes sin exponer
datos de Gmail fuera del equipo local o de una VPN privada.

**Current focus:** Milestone v10 — **auto-actualización** de la app macOS (menú
nativo + botón UI, verificación de firma, permiso explícito, auto-reinstalación).
Rama `feat/auto-update`. Milestone v9 (app macOS) mergeada a `main`
(`afad3a9`), con icono propio (`1c275b7`).

## Current Status

- **Funcionalidad:** madura. v1→v7.5 (Fases 1–29), v8 (refinamiento) y v9 (app
  macOS Developer ID + notarización) completados en `main`.
- **v9 — app macOS en `main`:** `paths.py` relocaliza el estado escribible a
  `~/Library/Application Support/GestorDeCorreos/`; `macos/` (pywebview, py2app,
  firma inside-out, notarización, DMG, icono). Verificada en el Mac.
- **v10 — Fase 36 (rama `feat/auto-update`):** `updater.py` + `/api/update/check`
  y `/api/update/install`; `VERSION` como fuente única; menú `pywebview` +
  botón `#upd-check`; `build_app.sh` emite `latest.json` + zip versionado.
  Código + tests hechos; **falta el flujo real con un Release de prueba**.
- **Scope Gmail:** `gmail.modify` para lectura/archivado/etiquetado;
  borrado permanente aislado en `delete_token.json` (`https://mail.google.com/`),
  desactivado por defecto.
- **Suite automatizada:** `156 tests` · **156 verdes** (v10 añadió
  `test_updater.py` +9 y 4 tests de servidor/frontend).
- **Testeo humano:** `TESTING_HUMANO.md` 30/30 ✅ (v7.5).

## Milestone v10 — Fases (rama `feat/auto-update`)

| Fase | Descripción | Estado |
|------|-------------|--------|
| 36 — Buscar actualizaciones | `updater.py` + endpoints + menú/botón; `latest.json` en GitHub Releases; verificación sha256 + codesign + team-id; permiso + auto-reinstalación | 🟡 Código + tests (156/156). Falta verificar el flujo real en el Mac (Release de prueba). Ver ADR-013. |

## Milestone v9 — App macOS (cerrado en `main`)

| Fase | Descripción | Estado |
|------|-------------|--------|
| 34 — App macOS (Developer ID) | `paths.py` + relocalización; `macos/` pywebview/py2app/firma inside-out/notarización/DMG/icono | ✅ Done (2026-09-09), mergeado a `main` (`afad3a9`) |
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

- 2026-09-09 — v10 / Fase 36 (rama `feat/auto-update`): `updater.py`
  (check/download+verify/install), `/api/update/check` y `/api/update/install`
  (el servidor re-verifica el manifiesto), `/api/status` con `app_version` +
  `bundled`, `VERSION` como fuente única, menú `pywebview` + botón `#upd-check`,
  `build_app.sh` emite `GestorDeCorreos-<v>.zip` + `latest.json`. +13 tests
  (156/156). Falta el flujo real con un Release de prueba. Ver ADR-013.
- 2026-09-09 — v9 mergeada a `main` (`afad3a9`) + icono propio (`1c275b7`,
  `macos/make_icon.py` desde `appicon-source.png`).
- 2026-09-09 — Fase 34 completada. Build en el Mac del usuario: framework Python
  de python.org (el de Homebrew no vale), `google` forzado fuera del zip
  (`__init__.py` + `packages`), firma **inside-out** de ~150 binarios `.so`
  (`codesign --deep` los dejaba sin firmar/timestamp → notarización Invalid).
  DMG firmado + notarizado + stapled OK. `spctl`/`codesign` verificados
  (Hardened Runtime, Developer ID `V29BTBRY6G`, timestamp). Ventana + login
  Gmail funcionando. Rama lista para merge a `main`.
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

**v10 / Fase 36 — verificar el auto-updater en el Mac** (rama `feat/auto-update`):

1. Merge de `feat/auto-update` a `main` (o probar en la rama).
2. `PYTHON=/usr/local/bin/python3.12 bash macos/build_app.sh` → genera
   `dist/GestorDeCorreos-1.0.0.zip`, `dist/latest.json`, DMG con el icono.
3. Publicar Release `v1.0.0` con esos assets:
   `gh release create v1.0.0 dist/GestorDeCorreos-1.0.0.zip dist/latest.json dist/GestorDeCorreos.dmg --title v1.0.0`.
4. Subir `VERSION` a `1.1.0`, rebuild, publicar Release `v1.1.0`.
5. Desde la `.app` v1.0.0 instalada: **Buscar actualizaciones** → debe detectar
   v1.1.0, pedir permiso, instalar y reiniciar. Cerrar UPD-06.

Pendientes menores:
- AppleEvent `odoc` para abrir un `.eml` con la app **ya abierta**.
- Fase 32 Stage C (`activeEmails`/`aiStatus`/`CATS` → `App.*`), opcional.
- Fase 35 — Mac App Store (rama aparte, shell Swift + WKWebView, App Sandbox).
- Sparkle (appcast + deltas) como alternativa futura al updater en Python.
