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
**Status:** Accepted (Fase 32, Stage A+B 2026-09-08; Stage C 2026-10-18)

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

Stage C (2026-10-18): se resuelve con **accessors**, no con repunte.
`app.js` define getters de solo lectura (`Object.defineProperties(App.state,…)`
para `activeEmails`/`aiStatus`, `Object.defineProperty(App.config,'CATS',…)`)
sobre sus propios `let`, que siguen reasignándose en `app.js` sin tocar sus
~36 usos. `summary.js` lee solo `App.state.activeEmails`, `App.state.aiStatus`
y `App.config.CATS`; un test del contrato prohíbe esas tres como global desnudo.

**Rationale:** `test_frontend_contract.py` fija fragmentos literales de código;
un refactor a módulos ES rompería decenas de aserciones y su valor como guardarraíl.
`App` como objeto plano da acceso explícito y documentado a la superficie
compartida con cambio mínimo.

**Consequences:** 3 aserciones de `test_frontend_contract.py` pasan a nombrar el
acceso vía `App` (intención preservada: excluye ocultos, endpoint correcto, avisa
antes de envío remoto). Nuevo `test_shared_namespace_is_declared_and_documented`.
Regla para el front (recogida en `AGENTS.md`): estado nuevo que cruce
`app.js`↔`summary.js` va en `App`, no en el global.

## ADR-012 — App macOS: Developer ID + notarización, estado en Application Support

**Date:** 2026-09-08
**Status:** Accepted · Fase 34 completada 2026-09-09 (DMG firmado + notarizado
verificado en el Mac). App Store diferido a Fase 35.

La herramienta se empaqueta como `.app` de macOS con ventana propia (WKWebView
vía `pywebview`) que arranca y detiene `server.py` por dentro. Se distribuye
**firmada con Developer ID Application, con Hardened Runtime, notarizada y
*stapled*, en un DMG** — fuera de la Mac App Store. La app web y la CLI siguen
igual: la `.app` es un artefacto adicional sobre el mismo backend.

**Rationale:** el usuario quiere distribuir con su cuenta Apple Developer. La Mac
App Store obliga a App Sandbox, revisión de App Review y encaja mal con una app
Python empaquetada con py2app que levanta un servidor local (patrón "wrapper de
web" + CPython sandboxed son focos de rechazo). Developer ID + notarización logra
distribución firmada y sin avisos de Gatekeeper reutilizando `server.py` sin
tocar la lógica.

**Consecuencias:**
- Nuevo `paths.py`: `data_dir()` (estado escribible) devuelve la carpeta del
  proyecto desde el código fuente y `~/Library/Application Support/GestorDeCorreos/`
  dentro del `.app` (`sys.frozen`); `resource_dir()` sirve `index.html`/`static`
  desde `Contents/Resources`. Override: `GESTOR_DATA_DIR`.
- `gmail_client`, `destructive_gmail`, `storage`, `server` toman sus rutas de
  `paths.py` conservando los nombres de constante (`CREDS`, `TOKEN`, `STATE_FILE`,
  `DELETE_TOKEN`, `EXPORTS_DIR`), así que los tests existentes no cambian.
- `credentials.json` y el resto de secretos del `.app` viven en Application
  Support, nunca en el bundle firmado.
- Dependencias de la app (`pywebview`, `pyobjc`, `py2app`) van en
  `requirements-macos.txt` aparte; `requirements.txt` (web/CLI) no crece.
- El build/firma/notarización se ejecutan en el Mac (`macos/build_app.sh`); el
  entorno de desarrollo Linux solo valida sintaxis y `paths.py` con tests.
- Fase 35 (Mac App Store) queda como milestone y rama aparte con shell nativo
  Swift + WKWebView.

## ADR-013 — Auto-actualización vía GitHub Releases (updater en Python)

**Date:** 2026-09-09
**Status:** Accepted y verificado en el Mac (2026-09-11, Fase 36, rama
`feat/auto-update`)
Superado por ADR-014 (Sparkle) desde la v1.3.0; sigue vigente como puente para
las 1.2.x y como respaldo si Sparkle no carga.

La app comprueba/descarga/instala actualizaciones con un **updater propio en
Python** (`updater.py` + endpoints `/api/update/*` + menú `pywebview`), no con
Sparkle. El feed es `latest.json` publicado como asset del último **GitHub
Release** (`edfrutos/gestor-correos-gmail`), que apunta a un `.zip` del `.app`
firmado+notarizado con el tag `vX.Y.Z`.

**Rationale:** Sparkle es el estándar pero exige embeber `Sparkle.framework` en
el bundle py2app, generar par de claves EdDSA y firmarlo/notarizarlo aparte —
mucha integración para una app Python con servidor local + pywebview. El updater
en Python reutiliza la arquitectura existente y se apoya en la firma Developer
ID + notarización de Apple para la autenticidad.

**Modelo de confianza** (cualquier fallo aborta la instalación):
1. `latest.json` por HTTPS (confianza TLS en GitHub).
2. `.zip` verificado por **sha256** contra el manifiesto (integridad).
3. `.app` verificado con `codesign --verify --strict`, `spctl -a` (notarizada) y
   `TeamIdentifier == V29BTBRY6G` (autenticidad). Un atacante no puede producir
   un build firmado por ese team y notarizado por Apple.
4. Índice del `.zip` validado **antes de extraer** (`_check_zip_entries`, ver
   addendum 2026-10-18).

**Consecuencias:**
- `/api/update/install` **re-consulta el manifiesto en el servidor** y usa su
  `url`/`sha256`; nunca instala una URL provista por el cliente.
- Instalación: permiso explícito → `ditto` de la `.app` nueva sobre la instalada
  vía helper *detached* que espera a que el proceso salga → relaunch; `osascript`
  con admin si el destino lo requiere.
- Desde el código fuente la comprobación informa pero la instalación automática
  está desactivada (`paths.is_bundled()`).
- `VERSION` (raíz) es la fuente única de versión: la leen `macos/setup.py`
  (`CFBundle*Version`) y `updater.py` (fallback fuera del bundle).
- Migrar a Sparkle (appcast + deltas) queda como opción futura.

**Addendum (2026-09-11):** la extracción del `.zip` descargado usaba
`zipfile`, que no reconstruye symlinks — corrompía `Versions/Current` del
framework de Python embebido y `codesign --verify --strict` fallaba tras
instalar. Fix: `ditto -x -k` (simétrico de `ditto -c -k` en
`build_app.sh`), con un reintento si `ditto` falla puntual creando algún
symlink. Como la extracción la ejecuta siempre el código ya cargado del
proceso en marcha (nunca el de la nueva versión descargada), una instancia
con el updater anterior a este fix no se autorepara actualizando — necesita
una reinstalación manual una vez para quedar en una versión con el fix.
Verificado en el Mac con Releases reales v1.1.0 → v1.2.0 → v1.2.1.

**Addendum (2026-10-18, revisión de seguridad del PR #2):** `ditto -x -k`
recrea los symlinks del archivo y se ejecutaba antes de cualquier
comprobación; la firma de (3) solo cubre la `.app`, y `latest.json` no va
firmado (el sha256 solo ata el zip al manifiesto del mismo Release). Quien
pudiera publicar assets en el Release (p. ej. con un token de GitHub, sin las
claves de Developer ID) podría envolver una `.app` legítima con entradas extra
(`../`, rutas absolutas o symlinks) que escribieran fuera del directorio
temporal durante la extracción. Fix, en dos barreras:
- `_check_zip_entries` (antes de `ditto`): una única raíz `*.app` (más
  `__MACOSX/` sin symlinks), sin rutas absolutas, `..`, `\` ni caracteres de
  control; cada symlink y el directorio padre de cada entrada se resuelven
  sobre un árbol virtual del propio zip (`_virtual_realpath`, sigue cadenas de
  symlinks como `realpath`) y deben quedar dentro de la `.app`.
- `_check_extracted_links` (tras `ditto`, antes de `codesign`): `realpath` de
  cada symlink real dentro de la `.app`.
- La `.app` a instalar es la raíz validada, no la primera que devuelva
  `glob`/`rglob`.
- (2ª revisión) Nombres **duplicados** rechazados: `ditto` aplica las entradas
  en orden, así que un symlink que sale, un fichero escrito a través de él y
  otro symlink inocuo con el mismo nombre al final burlaban un validador que
  solo mira el árbol final. Toda comparación usa la forma canónica de APFS
  (`_fs_key`: sin mayúsculas, NFD), porque `la`/`LA` o `é` NFC/NFD son la
  misma ruta en disco.

- (3ª revisión) **`ditto` fuera de la extracción.** Validar con `zipfile` y
  extraer con `ditto` deja un hueco en cada diferencia de interpretación del
  formato (p. ej. `zipfile` aplica el extra Info-ZIP Unicode Path `0x7075`,
  `ditto` puede usar el nombre de la cabecera local). Ahora `_extract_zip`
  extrae con el mismo parser y exactamente las rutas validadas: ficheros con
  `O_EXCL|O_NOFOLLOW`, symlinks creados al final (ninguna escritura los
  atraviesa; ninguna entrada puede colgar de uno), permisos sin
  setuid/setgid, `__MACOSX/` ignorado, tope de 2 GiB descomprimido. Revierte
  el addendum anterior (`ditto` en vez de `zipfile`) sin volver a su bug:
  los symlinks se recrean explícitamente.

Comprobado contra el zip real de v1.2.1 (1664 entradas, 4 symlinks internos
del framework de Python y `site.pyc`): valida y se extrae idéntico, entrada
por entrada (contenido, permisos y destino de cada symlink). Mismo matiz que el addendum
anterior: la protección la aplica el updater **ya instalado**, así que solo
cubre las actualizaciones posteriores a instalar una versión que la incluya.
Riesgo residual: un manifiesto firmado (p. ej. EdDSA, como Sparkle) cerraría
también la sustitución del zip por otra `.app` antigua firmada del mismo team
(downgrade); queda como mejora futura.

- (4ª revisión, tras publicar v1.2.2) **Downgrade cerrado sin firmar el
  manifiesto.** Después de verificar la firma, `_check_not_downgrade` lee el
  `CFBundleShortVersionString` del `Info.plist` extraído (sellado por la firma)
  y rechaza la instalación si no es mayor que la versión en ejecución. Un
  Release comprometido ya no puede colar una `.app` antigua legítima con un
  `latest.json` que diga otra versión: como mucho puede ofrecer una versión
  legítima más nueva, o no ofrecer ninguna (*freeze*, que el usuario ve como
  «estás en la última versión»). La firma del manifiesto queda solo como
  defensa en profundidad. Mismo matiz: protege desde la versión que la incluye.
- (2026-10-18) **`latest.json` firmado (Ed25519).** `build_app.sh` firma los
  bytes exactos del manifiesto con `macos/sign_manifest.py` y publica la firma
  aparte como `latest.json.sig` (base64); `fetch_manifest` la descarga y la
  verifica contra `UPDATE_PUBLIC_KEYS` antes de parsear el JSON. Firma
  separada en vez de un campo dentro del JSON: no hay que canonicalizar, y las
  versiones ≤ 1.2.3 (que solo leen `latest.json`) siguen actualizándose. La
  firma cubre `MANIFEST_SIG_CONTEXT + bytes` (separación de dominio). Sin
  firma, firma inválida o sin clave configurada → error, nunca "no hay
  versión" (*fail closed*). `cryptography` ya iba en la `.app` como
  dependencia de `google-auth`; ahora es explícita en `requirements.txt`.
  La clave privada vive fuera del repo (`UPDATE_SIGNING_KEY`); el build
  comprueba al empezar que corresponde a la embebida. Se admiten varias
  públicas para poder rotar. Quien tenga solo acceso a los assets del Release
  ya no puede ni cambiar la url/sha256 ni ofrecer una versión: queda el
  *replay* de un manifiesto firmado antiguo, que equivale a un *freeze*.

## ADR-014 — Sparkle 2 como updater de la app macOS (supera el updater en Python del ADR-013)

**Date:** 2026-10-20
**Status:** Accepted. Verificado en el Mac (v1.3.0 → v1.3.1)

Desde la v1.3.0 la `.app` lleva **Sparkle 2.9.6** (`Contents/Frameworks/Sparkle.framework`)
y lo arranca desde `macos/app_main.py` vía PyObjC (`SPUStandardUpdaterController`).
El feed es `appcast.xml`, publicado como asset de cada GitHub Release
(`SUFeedURL` = `…/releases/latest/download/appcast.xml`).

**Rationale:** diálogo estándar de macOS (notas, «Omitir esta versión»,
«Recordar más tarde»), comprobación automática diaria y un instalador probado
por miles de apps, en vez de mantener el nuestro (`ditto` + helper detached).
Lo que en 2026-09 hacía caro a Sparkle (claves EdDSA, firma aparte) ya estaba
resuelto: el manifiesto firmado de la v1.2.4 usa Ed25519.

**Decisiones:**
- **Misma clave Ed25519** que `latest.json`: `SUPublicEDKey` = la pública de
  `updater.UPDATE_PUBLIC_KEYS[0]` en base64. Sparkle firma los bytes del zip
  sin contexto y el manifiesto lleva `MANIFEST_SIG_CONTEXT` delante; como un zip
  empieza por `PK\x03\x04`, ninguna firma vale para la otra.
- El appcast lo genera `macos/make_appcast.py` en Python (sin `generate_appcast`
  ni `sign_update`), verificando la firma con la clave embebida.
- Sparkle descargado en `build_app.sh` con versión y sha256 fijados; se quitan
  los XPC services (solo los usa una app con App Sandbox). Firma inside-out:
  `Autoupdate`, `Updater.app` y después el framework.
- Sparkle además valida que la nueva `.app` está firmada con la misma identidad
  Developer ID que la instalada.
- **Puente:** se sigue publicando `latest.json(.sig)`. Las 1.2.x solo conocen el
  updater en Python y por ahí llegan a la 1.3.0; desde ahí actualiza Sparkle.
- **Respaldo:** si el framework no está (desde fuente) o no carga,
  `SparkleUpdater.available` es False y menú y botón usan `updater.py`.
- Deltas (`BinaryDelta`) quedan fuera: exigen conservar la `.app` anterior en
  cada build. Pueden añadirse sin tocar la app.

**Addendum (2026-10-20, Fase 38 — deltas, v1.3.2):** en vez de conservar la
`.app` anterior, `build_app.sh` descarga el zip del último Release
(`macos/delta_base.py`) y solo lo usa si su longitud y su `sparkle:edSignature`
del appcast publicado casan con la clave embebida (y la URL es un asset del
propio repo y tag); así el delta parte exactamente de lo que tienen instalado
los usuarios. `BinaryDelta` (del mismo tarball de Sparkle, sha256 fijado) crea
`GestorDeCorreos-<v>-from-<anterior>.delta`; antes de publicarlo se aplica a la
base y la `.app` resultante debe pasar `codesign --verify --deep --strict` y
tener el mismo CDHash que la compilada. El delta se firma con la misma clave y
va en `<sparkle:deltas>` (`sparkle:deltaFrom`). Un solo delta, desde la versión
inmediatamente anterior; el resto descarga el zip completo. Sin base (primer
Release, red) o si el delta no verifica, se publica sin delta; si la base
publicada no casa con su firma, el build se detiene.

## ADR-015 — Mac App Store como variante de build sobre py2app (Fase 35)

**Date:** 2026-10-20
**Status:** Accepted, pendiente de verificar en el Mac y en App Review (v1.4.0, rama `feat/mac-app-store`)

La versión de la Mac App Store sale del mismo código y del mismo bundle py2app +
pywebview que la de Developer ID, con otra receta de build
(`macos/build_mas.sh`), en vez del shell nativo en Swift que planteaba el
ADR-012.

**Rationale:** un shell en Swift duplicaría la app (ventana, menú, apertura de
`.eml`, selector de carpetas) para seguir lanzando el mismo backend en Python,
que es lo que App Review evalúa. App Sandbox no impide nada de lo que hace la
app: el servidor local va con `network.server`, Gmail/OAuth/IA con
`network.client`, y lo que el usuario elige en un panel nativo queda accesible.
Lo único incompatible con la tienda es actualizarse sola, y eso se desactiva.

**Decisiones:**
- `paths.distribution()`: `"mas"` si el bundle trae `Contents/Resources/DISTRIBUTION`
  (lo escribe `build_mas.sh`); `"direct"` en el resto. Override `GESTOR_DISTRIBUTION`.
- **Sin actualizaciones propias** (guía 2.4.5): `setup.py` no pone las claves de
  Sparkle, `build_mas.sh` comprueba que no va `Sparkle.framework`, la app no crea
  `SparkleUpdater` ni el menú, `updater` no consulta ni instala y
  `/api/update/install` responde 403. La UI oculta ⟳ con `distribution === 'mas'`.
- **OAuth en el navegador del sistema** (las dos variantes): `webbrowser` usa
  `osascript` en macOS, que el sandbox bloquea, y la app corría con HEADLESS=1,
  que no abría el navegador. `app_main` registra un controlador de `webbrowser`
  con NSWorkspace y `gmail_client.run_oauth_flow` lo usa también para el permiso
  de borrado; timeout de 300 s para no dejar peticiones colgadas.
- **credentials.json desde la app**: «📄 Importar credentials.json…» valida un
  cliente de escritorio (`installed` con `client_id`/`client_secret`), lo copia
  con permisos 600 y descarta el token si era de otro cliente. La build de la
  tienda puede llevar su propio cliente (`MAS_OAUTH_CLIENT` →
  `Resources/oauth_client.json`), que se copia a la carpeta de datos marcado con
  `gestor_bundled`; un `credentials.json` del usuario nunca se sobrescribe.
- **Carpeta de respaldo**: en la tienda, `JsApi.pick_folder` guarda un
  *security-scoped bookmark* (`bookmarks.json`) y la app lo reactiva al arrancar.
- **Firma**: sin Hardened Runtime (la tienda no lo pide, así que sobran los
  `cs.*`); ejecutables anidados con `app-sandbox` + `inherit`; bundle con
  `entitlements-mas.plist`, cuyo `application-identifier` se comprueba contra el
  perfil antes de firmar. Se quita el `Python.app` anidado de `Python.framework`.
  `MAS_LOCAL=1` firma con Developer ID y sin las claves del perfil para probar el
  sandbox sin App Store Connect.
- Mismo bundle ID que la variante de Developer ID; los datos no migran (otro
  contenedor).

**Consecuencias / riesgos:**
- La publicación depende de pasos fuera del repo: certificados y perfil de
  Apple, ficha en App Store Connect, y en Google la pantalla de consentimiento.
  `gmail.modify` es un permiso restringido: para salir de *Testing* (100
  usuarios, tokens de 7 días) Google exige verificación y una evaluación CASA
  anual. Detalle en `docs/MAC_APP_STORE.md`.
- Riesgo de rechazo por la guía 4.2 (interfaz HTML). Plan B: el shell Swift del
  ADR-012 lanzando el mismo backend.
