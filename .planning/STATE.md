---
gsd_state_version: 1.0
milestone: v10
milestone_name: Auto-actualización
status: completed
last_updated: "2026-09-11T00:00:00.000Z"
branch: main
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 0
  completed_plans: 0
  percent: 100
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
Verificada de extremo a extremo en el Mac (v1.1.0 → v1.2.0 → v1.2.1, releases
reales en GitHub). Mergeada a `main` en el PR #2 (`524c015`, 2026-10-18), con
el endurecimiento de la extracción del zip. Milestone
v9 (app macOS) mergeada a `main` (`afad3a9`), con icono propio (`1c275b7`).

## Current Status

- **Funcionalidad:** madura. v1→v7.5 (Fases 1–29), v8 (refinamiento) y v9 (app
  macOS Developer ID + notarización) completados en `main`.
- **v9 — app macOS en `main`:** `paths.py` relocaliza el estado escribible a
  `~/Library/Application Support/GestorDeCorreos/`; `macos/` (pywebview, py2app,
  firma inside-out, notarización, DMG, icono). Verificada en el Mac.
- **v10 — Fase 36 (rama `feat/auto-update`):** `updater.py` + `/api/update/check`
  y `/api/update/install`; `VERSION` como fuente única; menú `pywebview` +
  botón `#upd-check`; `build_app.sh` emite `latest.json` + zip versionado y
  DMG con acceso directo a `/Applications`. **Verificado en el Mac con
  Releases reales** (v1.1.0 → v1.2.0 → v1.2.1): detecta, descarga, verifica
  firma y se auto-reinstala. UPD-06 cerrado.
- **Aprendizaje clave (extracción de zip):** la extracción original usaba
  `zipfile`, que no reconstruye symlinks — corrompía `Versions/Current` del
  framework de Python embebido y `codesign --verify` fallaba tras instalar
  la actualización. Fix: `ditto -x -k` (simétrico de `ditto -c -k` en
  `build_app.sh`), con un reintento si `ditto` falla puntual creando algún
  symlink. **Importante:** ese fix vive en el updater de la app que hace la
  extracción — una instancia con el updater viejo (`zipfile`) no se autorepara
  actualizando; necesita una reinstalación manual una vez.
  **2026-10-18:** `ditto -x -k` se sustituye por `_extract_zip` (Python, mismo
  parser que la validación del zip; recrea symlinks y permisos). Reproduce el
  zip real de v1.2.1 entrada por entrada (1664/1664). Ver ADR-013.
- **Scope Gmail:** `gmail.modify` para lectura/archivado/etiquetado;
  borrado permanente aislado en `delete_token.json` (`https://mail.google.com/`),
  desactivado por defecto.
- **Suite automatizada:** `209 tests` · **209 verdes**.
- **Testeo humano:** `TESTING_HUMANO.md` 37/38 (pendiente §9 «Manifiesto firmado»; 2026-10-18: §7 `odoc` y §9
  validación del zip verificados en el Mac; §2–§6 repasados tras Stage C).

## Milestone v10 — Fases (rama `feat/auto-update`)

| Fase | Descripción | Estado |
|------|-------------|--------|
| 36 — Buscar actualizaciones | `updater.py` + endpoints + menú/botón; `latest.json` en GitHub Releases; verificación sha256 + codesign + team-id; permiso + auto-reinstalación | ✅ Done (2026-09-11). Verificado en el Mac con Releases reales (v1.1.0→v1.2.0→v1.2.1). Ver ADR-013. |

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
| 32 — Encapsulación JS | Stage A (relocación `summaryDays`/`summaryData`, cabecera SHARED SURFACE, sin `onclick` inline) + Stage B (`static/shared.js` con `App`; `API`/`deleted` compartidos vía `App.*`) | ✅ Done (2026-09-08). Stage C (`activeEmails`/`aiStatus`/`CATS` como getters en `App`) ✅ 2026-10-18 |

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
- Updater: `latest.json` va firmado (Ed25519, `latest.json.sig`, rama
  `feat/signed-manifest`); el zip se valida antes de extraer, la `.app` por
  firma + Team ID y su versión (del `Info.plist` sellado) debe ser mayor que
  la instalada (ADR-013, addenda 2026-10-18). Queda el *freeze* (replay de un
  manifiesto firmado antiguo). Cada protección del updater solo actúa a
  partir de la versión que la incluye: ≤ v1.2.1 sin validación del zip;
  ≤ v1.2.2 sin anti-downgrade; ≤ v1.2.3 sin firma del manifiesto.
- La clave privada de `UPDATE_SIGNING_KEY` no tiene respaldo en el repo: si
  se pierde, las versiones que verifican la firma no reciben más
  actualizaciones sin reinstalación manual.
- `app.js` sigue usando sus `let` de nivel superior internamente (`summary.js` ya
  solo lee vía `App.*`); cualquier refactor mayor (módulos ES) debe respetar el
  contrato literal de `test_frontend_contract.py`.

## Last Activity

- 2026-10-18 — **Firma de `latest.json`** (rama `feat/signed-manifest`):
  `fetch_manifest` exige `latest.json.sig` (Ed25519 sobre
  `MANIFEST_SIG_CONTEXT + bytes`) y la verifica contra `UPDATE_PUBLIC_KEYS`
  antes de parsear; *fail closed* (sin firma ≠ "no hay versión").
  `macos/sign_manifest.py` (`keygen`/`check`/`sign`); `build_app.sh` exige
  `UPDATE_SIGNING_KEY`, comprueba la clave antes de compilar y publica la
  `.sig`. `cryptography` explícita en `requirements.txt`. +14 tests, 209/209.
  Clave real generada en el Mac y pública embebida; `VERSION` 1.2.4.
  Pendiente: Release v1.2.4 y §9 «Manifiesto firmado» desde v1.2.4 → siguiente.

- 2026-10-18 — **Release v1.2.3 publicado** (tag en `3eb70df`, PR #6:
  anti-downgrade). Actualización 1.2.2 → 1.2.3 verificada en el Mac (§9);
  §7 (`odoc`) y repaso de §2–§6 tras Stage C, todo correcto. Testeo humano 37/37.
- 2026-10-18 — **Release v1.2.2 publicado** (tag en `b250f0a`, primer tag que
  coincide con el código compilado). Build firmado y notarizado (`.app` y DMG
  aceptados por `spctl`); actualización 1.2.1 → 1.2.2 verificada en el Mac.
  Después (rama `fix/update-no-downgrade`): `_check_not_downgrade` rechaza una
  `.app` cuya versión (del `Info.plist` sellado por la firma) no sea mayor que
  la instalada. +3 tests, 195/195.
- 2026-10-18 — Preparación de v1.2.2 (rama `release/1.2.2`): `VERSION` 1.2.2;
  `build_app.sh` autocomprueba el zip con `updater._check_zip_entries` antes
  de publicar y el comando de Release lleva `--target <commit compilado>`
  (avisa si hay cambios sin commitear). PR #2 (`524c015`) y PR #3 (`ff54b40`)
  mergeados a `main`.

- 2026-10-18 — `/api/read-eml` limitado a `.eml` (rama `feat/macos-odoc`):
  antes `?path=` leía cualquier fichero local. Ahora resuelve la ruta (sigue
  symlinks) y exige sufijo `.eml` + fichero regular, tanto para `path` como para
  `file` en `/exports` (400 si no es `.eml`, 404 si no existe). +5 tests, 167/167.
- 2026-10-18 — AppleEvent `odoc` (rama `feat/macos-odoc`): `macos/app_main.py`
  añade `application:openFiles:` al `AppDelegate` de pywebview; `EmlOpener`
  abre el visor vía `openEmlReader` sin recargar o encola hasta `loaded` en
  arranque en frío. `?view=` ahora va con la ruta URL-encoded. +5 tests
  (`tests/test_macos_app.py`), suite 162/162. Falta verificación en el Mac.
- 2026-10-18 — Fase 32 Stage C (rama `feat/js-stage-c`): `app.js` expone
  `activeEmails`/`aiStatus`/`CATS` como getters en `App.state`/`App.config`;
  `summary.js` sin globales desnudas de estado. Contrato reforzado (sin nuevos
  tests, +6 aserciones). Suite 157/157. Ver ADR-011.
- 2026-10-18 — Hallazgo de seguridad (Cursor) en PR #2, severidad media:
  `ditto -x -k` extraía el zip de actualización antes de validar nada.
  Fix en `updater.py`: `_check_zip_entries` valida el índice del zip (una
  sola `.app` raíz, sin `..`/absolutas, symlinks resueltos dentro de la
  `.app` siguiendo cadenas) antes de `ditto`, y `_check_extracted_links`
  re-comprueba con `realpath` tras extraer. Probado contra el zip real de
  v1.2.1. 2ª revisión (otro hallazgo medio): rechazar nombres duplicados
  (ditto aplica en orden) y comparar rutas como APFS (sin mayúsculas, NFD).
  3ª revisión (otro medio): validar con `zipfile` y extraer con `ditto` deja
  huecos por diferencias de parser (p. ej. extra Unicode Path `0x7075` frente
  al nombre de la cabecera local). Fix de raíz: `ditto` fuera de la
  extracción; `_extract_zip` extrae con el mismo parser y las mismas rutas
  validadas (`O_EXCL|O_NOFOLLOW`, symlinks al final, sin setuid, tope de 2 GiB
  descomprimido, nada bajo un symlink). Zip real de v1.2.1 reproducido
  1664/1664. 181/181. Pendiente: Release nuevo y repetir §9 en el Mac.
- 2026-09-11 — v10 / Fase 36 cerrado: fix de extracción (`ditto` en vez de
  `zipfile`, preserva symlinks del framework de Python — `0a6afbb`) +
  corrección de `VERSION` que se había quedado en 1.1.0 pese al mensaje de
  commit (`6075f74`) + reintento de `ditto` ante fallo puntual de symlink y
  DMG con acceso a `/Applications` (`72a119f`) + `VERSION` 1.2.1 (`c1400e1`).
  Verificado en el Mac de punta a punta con Releases reales v1.1.0 → v1.2.0 →
  v1.2.1: "Buscar actualizaciones" detecta, descarga, verifica firma e instala.
  UPD-06 cerrado. Suite 157/157.
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

**v1.2.3 publicado** (tag `v1.2.3` en `3eb70df`) y verificado en el Mac;
testeo humano 37/37. `v1.2.2` (`b250f0a`) y `v1.2.3` son los primeros tags que
coinciden con lo compilado; `v1.2.0`/`v1.2.1` siguen en `fe55367`.

Firma de `latest.json` (rama `feat/signed-manifest`, UPD-07): clave generada
en el Mac (`~/.config/gestor-correos/update_signing.pem`, pública `39a60417…`
embebida en `updater.UPDATE_PUBLIC_KEYS`), `VERSION` 1.2.4. Falta:
`UPDATE_SIGNING_KEY` en `macos/build.env`, merge, Release v1.2.4 con
`latest.json.sig` (1.2.3 → 1.2.4 sigue sin verificar firma) y después §9
«Manifiesto firmado» con v1.2.4 → siguiente Release. Próxima Release: mismo flujo (subir `VERSION`,
`build_app.sh`, el `gh release create … --target <commit>` que imprime).

Otros pendientes:
- Fase 35 — Mac App Store (rama aparte, shell Swift + WKWebView, App Sandbox).
- Sparkle (appcast + deltas) como alternativa futura al updater en Python.
