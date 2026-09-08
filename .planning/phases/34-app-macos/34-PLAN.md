---
phase: 34
plan_id: 34-PLAN
milestone: v9
title: App macOS nativa (Developer ID + notarización)
branch: feat/macos-app
depends_on: []
requirements_addressed: [MAC-01, MAC-02, MAC-03, MAC-04, MAC-05]
files_modified:
  - paths.py                 # nuevo
  - gmail_client.py
  - destructive_gmail.py
  - storage.py
  - server.py
  - macos/app_main.py        # nuevo
  - macos/setup.py           # nuevo (py2app)
  - macos/entitlements.plist # nuevo
  - macos/Info.plist.extra   # nuevo (fragmento)
  - macos/build_app.sh       # nuevo
  - macos/README.md          # nuevo
  - requirements-macos.txt   # nuevo
  - .gitignore
  - README.md
  - tests/test_paths.py      # nuevo
autonomous: false   # build/firma/notarización se ejecutan en el Mac del usuario
---

# Phase 34 Plan: App macOS nativa

## Objetivo

Empaquetar la herramienta como una app `.app` de macOS con ventana propia
(WKWebView vía `pywebview`) que arranca y detiene `server.py` como subproceso,
firmada con **Developer ID Application**, con **Hardened Runtime**, notarizada y
distribuida en DMG. La **app web sigue funcionando igual** (`.venv/bin/python
server.py`): la app macOS es un artefacto adicional que reutiliza backend y
frontend sin cambios de comportamiento.

Mac App Store queda como **hito posterior** (rama aparte, shell nativo Swift):
ver `## App Store (futuro)`.

## Entorno

El desarrollo actual corre en Linux: **no se puede** ejecutar `py2app`, `Xcode`,
`codesign` ni `notarytool` aquí. Esta fase entrega el andamiaje y los tests
verificables en Python; el build/firma/notarización los ejecuta el usuario en su
Mac siguiendo `macos/README.md`.

## Must Haves

- La app web y la CLI no cambian de comportamiento. Ejecutar desde el código
  fuente sigue usando la carpeta del proyecto para todo el estado.
- Dentro del `.app` (bundle de solo lectura y firmado), **ningún** archivo
  escribible vive en el bundle: `credentials.json`, `token.json`,
  `delete_token.json`, `delete_token.revoked`, `app_state.json`, `exports/` y
  `.env` opcional se relocalizan a `~/Library/Application Support/GestorDeCorreos/`.
- Los assets de solo lectura (`index.html`, `static/*`) se sirven desde
  `Contents/Resources/` del bundle.
- OAuth de Gmail funciona desde la app (abre el navegador del sistema; el
  `redirect_uri` de bucle local sigue en `localhost`).
- Hardened Runtime + entitlements mínimos; sin APIs privadas; sin `.env` embebido.
- La suite `pytest` sigue verde; se añade `tests/test_paths.py`.

## Diseño: `paths.py`

Módulo único que resuelve dos carpetas y lo usan todos los demás módulos:

| Función | Devuelve |
|---------|----------|
| `data_dir()` | Carpeta escribible. Prioridad: `GESTOR_DATA_DIR` (env) → si `sys.frozen` (bundle) `~/Library/Application Support/GestorDeCorreos/` → si no, carpeta del proyecto. Crea la carpeta. |
| `resource_dir()` | Assets de solo lectura. `RESOURCEPATH` (env que py2app define) → si bundle, `Contents/Resources` → si no, carpeta del proyecto. |
| `data_path(name)` | `data_dir() / name` |
| `is_bundled()` | `bool(getattr(sys, 'frozen', False))` |

Los tests existentes monkeypatchean las constantes finales
(`gmail_client.TOKEN`, `storage.STATE_FILE`, `destructive_gmail.DELETE_TOKEN`,
`server.EXPORTS_DIR`), así que se conservan esos nombres y solo cambia **cómo se
calculan**. Compatibilidad hacia atrás garantizada para código ejecutado desde
fuente.

## Tasks

<task id="34-01" name="Módulo paths.py + tests" type="execute">
  <action>
    Crear `paths.py` con `data_dir`, `resource_dir`, `data_path`, `is_bundled`
    según el diseño. Crear `tests/test_paths.py`: (a) sin `GESTOR_DATA_DIR` y sin
    frozen → `data_dir()` == carpeta del proyecto; (b) con `GESTOR_DATA_DIR` a un
    `tmp_path` → lo usa y lo crea; (c) `is_bundled()` False en test;
    (d) `resource_dir()` respeta `RESOURCEPATH`.
  </action>
  <acceptance_criteria>
    <criterion>`pytest tests/test_paths.py` verde</criterion>
    <criterion>`data_dir()` con override crea la carpeta si no existe</criterion>
  </acceptance_criteria>
</task>

<task id="34-02" name="Relocalizar estado escribible a data_dir()" type="execute">
  <read_first>
    <file>gmail_client.py</file><file>destructive_gmail.py</file>
    <file>storage.py</file><file>server.py</file>
    <file>tests/test_storage.py</file><file>tests/test_gmail_client.py</file>
    <file>tests/test_destructive_gmail.py</file>
  </read_first>
  <action>
    - `gmail_client.py`: `CREDS = data_path('credentials.json')`,
      `TOKEN = data_path('token.json')`.
    - `destructive_gmail.py`: `CREDS`, `DELETE_TOKEN`, `DELETE_REVOKED` vía `data_path`.
    - `storage.py`: `STATE_FILE = data_path('app_state.json')`.
    - `server.py`: `EXPORTS_DIR = data_path('exports')` (+ `mkdir`);
      `load_env()` lee `data_dir() / '.env'` **y** además el `.env` del proyecto
      si existe (para no romper la CLI); assets (`STATIC_FILES`, `index.html`)
      desde `resource_dir()`.
    Mantener los nombres de constante intactos. No tocar la lógica de negocio.
  </action>
  <acceptance_criteria>
    <criterion>`pytest` completo verde sin cambios en los tests existentes</criterion>
    <criterion>Ejecutado desde fuente, las rutas resueltas == carpeta del proyecto</criterion>
    <criterion>`grep -n "Path(__file__).parent" server.py gmail_client.py destructive_gmail.py storage.py` solo aparece dentro de paths.py</criterion>
  </acceptance_criteria>
</task>

<task id="34-03" name="Entry point pywebview (macos/app_main.py)" type="execute">
  <action>
    `macos/app_main.py`: (1) fija `GESTOR_DATA_DIR` si no está y arranca
    `server.py` en un hilo/subproceso en `127.0.0.1:PORT` (puerto libre si 8765
    ocupado); (2) espera a que responda `/api/status`; (3) abre una ventana
    `webview.create_window("Gestor de Correos", "http://127.0.0.1:PORT", ...)`;
    (4) al cerrar la ventana, detiene el servidor limpiamente; (5) soporta abrir
    un `.eml` recibido por argv / Apple Event `odoc` → navega a `/?view=<ruta>`.
    Reutiliza `server.main()`/`ThreadingHTTPServer` sin duplicar lógica.
  </action>
  <acceptance_criteria>
    <criterion>`python3 -m py_compile macos/app_main.py` OK</criterion>
    <criterion>Documentado cómo se prueba en el Mac (sin firmar): `python macos/app_main.py`</criterion>
  </acceptance_criteria>
</task>

<task id="34-04" name="py2app: setup.py, Info.plist, entitlements" type="execute">
  <action>
    - `macos/setup.py`: config py2app — `APP=['app_main.py']`,
      `DATA_FILES` con `index.html` y `static/`, `OPTIONS` con
      `includes`/`packages` (googleapiclient, google_auth_*, pywebview, objc…),
      `plist` (CFBundleIdentifier `com.edefruto.gestorcorreos`, versión,
      `LSMinimumSystemVersion`, `CFBundleDocumentTypes` para `.eml`,
      `NSHumanReadableCopyright`), `codesign` diferido al script.
    - `macos/entitlements.plist`: Hardened Runtime — `com.apple.security.cs.allow-jit`
      solo si hace falta, `com.apple.security.network.client`,
      `com.apple.security.network.server` (bucle local), sin sandbox (Developer ID
      no lo exige; el hito App Store lo añadirá).
    - `macos/Info.plist.extra`: fragmento con los tipos de documento y
      `LSUIElement=false`.
  </action>
  <acceptance_criteria>
    <criterion>`python3 -m py_compile macos/setup.py` OK</criterion>
    <criterion>`entitlements.plist` es plist válido (parseable)</criterion>
  </acceptance_criteria>
</task>

<task id="34-05" name="build_app.sh: build + firma + notarización + DMG" type="execute">
  <action>
    Script idempotente y parametrizado por variables de entorno
    (`DEV_ID_APP="Developer ID Application: … (TEAMID)"`, `TEAM_ID`,
    `AC_PROFILE` para `notarytool --keychain-profile`). Pasos:
    1. `python -m venv build-venv && pip install -r requirements.txt -r requirements-macos.txt`
    2. `python macos/setup.py py2app`
    3. `codesign --deep --force --options runtime --entitlements macos/entitlements.plist --sign "$DEV_ID_APP" dist/*.app`
    4. `ditto -c -k --keepParent dist/*.app dist/app.zip`
    5. `xcrun notarytool submit dist/app.zip --keychain-profile "$AC_PROFILE" --wait`
    6. `xcrun stapler staple dist/*.app`
    7. `hdiutil create -volname "Gestor de Correos" -srcfolder dist/*.app -ov -format UDZO dist/GestorDeCorreos.dmg`
    8. `codesign --sign "$DEV_ID_APP" dist/GestorDeCorreos.dmg` + `stapler staple` del DMG.
    Con `set -euo pipefail` y checks de que las variables existen.
  </action>
  <acceptance_criteria>
    <criterion>`bash -n macos/build_app.sh` OK</criterion>
    <criterion>El script falla con mensaje claro si faltan `DEV_ID_APP`/`AC_PROFILE`</criterion>
  </acceptance_criteria>
</task>

<task id="34-06" name="requirements-macos.txt + .gitignore + docs" type="execute">
  <action>
    - `requirements-macos.txt`: `pywebview`, `pyobjc-core`, `pyobjc-framework-Cocoa`,
      `pyobjc-framework-WebKit`, `py2app`.
    - `.gitignore`: `macos/build/`, `macos/dist/`, `build-venv/`, `*.dmg`, `*.app/`.
    - `README.md`: sección "App de escritorio para macOS" (qué es, que coexiste
      con la web, cómo se prueba sin firmar, y remisión a `macos/README.md`).
    - `macos/README.md`: guía completa en el Mac — prerequisitos (Xcode CLT,
      cuenta Apple Developer, cert Developer ID, `notarytool` keychain profile),
      variables de entorno, `bash macos/build_app.sh`, dónde queda el DMG, dónde
      poner `credentials.json` (`~/Library/Application Support/GestorDeCorreos/`),
      y solución de problemas típicos (Gatekeeper, "app is damaged", timeouts de
      notarización).
  </action>
  <acceptance_criteria>
    <criterion>`.gitignore` cubre los artefactos de build</criterion>
    <criterion>`macos/README.md` lista los comandos exactos en orden</criterion>
  </acceptance_criteria>
</task>

<task id="34-07" name="Cierre: docs de planning + requisitos" type="execute">
  <action>
    `.planning/STATE.md`, `.planning/ROADMAP.md` (Milestone 9),
    `.planning/REQUIREMENTS.md` (MAC-01..05), `.planning/DECISIONS.md`
    (ADR-012: app macOS Developer ID + relocalización de estado a
    Application Support; App Store diferido a shell Swift).
  </action>
</task>

## Requisitos

- **MAC-01**: Existe una `.app` de macOS con ventana propia que muestra la UI
  local y arranca/detiene `server.py`, sin romper la app web ni la CLI.
- **MAC-02**: Todo el estado escribible del `.app` vive en
  `~/Library/Application Support/GestorDeCorreos/`, nunca dentro del bundle.
- **MAC-03**: El `.app` se firma con Developer ID Application, con Hardened
  Runtime y entitlements mínimos, y se notariza y *staplea*.
- **MAC-04**: El build es reproducible con `macos/build_app.sh` + variables de
  entorno documentadas; produce un DMG firmado y notarizado.
- **MAC-05**: `credentials.json` y el flujo OAuth de Gmail funcionan desde la app
  (el usuario coloca `credentials.json` en Application Support).

## Riesgos

- **py2app + dependencias Google:** `googleapiclient` usa data files y descubrimiento
  dinámico; puede necesitar `includes`/`packages` explícitos y `--no-strip`.
  Mitigación: lista de `includes` en `setup.py` y sección de troubleshooting.
- **Notarización lenta / rechazo:** timeouts o binarios sin firmar dentro del
  bundle. Mitigación: `codesign --deep`, `notarytool --wait`, log de `notarytool log`.
- **Puerto ocupado:** otra instancia (web/CLI) en 8765. Mitigación: la app elige
  puerto libre y pasa `--open` a la instancia activa si procede.
- **OAuth en bucle local dentro del bundle:** el `redirect_uri` debe seguir
  siendo `http://localhost` registrado en Google Cloud. Sin cambios de scope.
- **No verificable en este entorno:** build/firma/notarización se prueban solo en
  el Mac. Mitigación: `py_compile`/`bash -n` aquí + checklist en `macos/README.md`.

## App Store (futuro)

Rama y milestone aparte. Implica: shell nativo **Swift/SwiftUI + WKWebView**,
App Sandbox obligatorio, `server.py` como *helper* bundled sandboxed en bucle
local (o port parcial a Swift), cert *3rd Party Mac Developer*, revisión de App
Review (riesgo por patrón "wrapper de web"). No se aborda en la Fase 34.
