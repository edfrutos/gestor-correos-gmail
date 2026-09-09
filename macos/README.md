# App de escritorio para macOS

Empaqueta el Gestor de Correos como una `.app` con ventana propia (WKWebView vía
`pywebview`) que arranca y detiene `server.py` por dentro. **La app web y la CLI
siguen funcionando igual** (`.venv/bin/python server.py`): esto es un artefacto
adicional que reutiliza el mismo backend.

Vía de distribución: **Developer ID + notarización** (DMG fuera de la Mac App
Store). El hito Mac App Store se abordará en una rama aparte con un shell nativo
Swift.

---

## Prueba rápida sin empaquetar

macOS bloquea `pip` sobre el Python de Homebrew (`externally-managed-environment`,
PEP 668). **Siempre en un venv** — no uses `--break-system-packages`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-macos.txt
.venv/bin/python macos/app_main.py            # abre la ventana
.venv/bin/python macos/app_main.py correo.eml # abre un .eml en el visor
```

Si `app_main.py` dice *"Falta pywebview"*, es que lo lanzaste con el `python3`
del sistema en vez de `.venv/bin/python`.

Datos escribibles en este modo (ejecutado desde el código fuente): la **carpeta
del proyecto**, como siempre. Coloca ahí `credentials.json`.

---

## Build firmado + notarizado (produce el DMG)

### Requisitos en el Mac

- **Xcode Command Line Tools**: `xcode-select --install`
- **Python 3.11+ con *framework build*** para py2app. El de **Homebrew no sirve**
  (produce un `.app` que no arranca). Usa el instalador de
  [python.org](https://www.python.org/downloads/macos/) o pyenv con
  `PYTHON_CONFIGURE_OPTS="--enable-framework"`, y pásalo al script:
  `PYTHON=/usr/local/bin/python3.12 bash macos/build_app.sh`.
  El de Homebrew sí vale para la *prueba rápida sin empaquetar* de arriba.
- **Cuenta Apple Developer** de pago (99 €/año). La cuenta gratuita no da
  certificados Developer ID ni notarización.
- **Certificado *Developer ID Application*** instalado en el llavero.
- **Perfil de notarytool** guardado una vez (ver abajo).

Las dos variables de entorno que consume `macos/build_app.sh`:

| Variable | Qué es | De dónde sale |
|---|---|---|
| `DEV_ID_APP` | Nombre completo del certificado de firma | `security find-identity -v -p codesigning` → copia la línea `"Developer ID Application: Tu Nombre (TEAMID)"` **entre comillas**. Si no aparece: developer.apple.com → *Certificates* → **+** → *Developer ID Application* → descarga el `.cer` y doble clic para instalarlo en el llavero. |
| `AC_PROFILE` | **Nombre que eliges tú** para la entrada de credenciales de notarización guardada en el llavero | No se "obtiene": lo creas con `xcrun notarytool store-credentials "<nombre>"` (abajo). Puede ser `gestor-notary`, `mi-perfil`, lo que quieras; solo debe coincidir con lo que exportas. |

#### Crear el perfil de notarytool (una sola vez)

`store-credentials` guarda en el llavero un paquete con tu Apple ID + Team ID +
secreto, bajo el nombre que le des. Dos formas de autenticar:

**Opción A — contraseña específica de app** (la más simple):

```bash
xcrun notarytool store-credentials "gestor-notary" \
    --apple-id "TU_APPLE_ID@ejemplo.com" \
    --team-id "TEAMID10CH" \
    --password "xxxx-xxxx-xxxx-xxxx"
```

| Dato | De dónde sale |
|---|---|
| `--apple-id` | El email de tu cuenta Apple Developer. |
| `--team-id` | [developer.apple.com/account](https://developer.apple.com/account) → **Membership details** → *Team ID* (10 caracteres). También va entre paréntesis en la salida de `security find-identity`. |
| `--password` | **Contraseña específica de app**, NO tu contraseña de Apple. [account.apple.com](https://account.apple.com) → *Iniciar sesión y seguridad* → **Contraseñas específicas de app** → **+** → nómbrala (p. ej. "notarytool") → copia el `xxxx-xxxx-xxxx-xxxx`. |

**Opción B — clave de API de App Store Connect** (sin contraseña de app):

```bash
xcrun notarytool store-credentials "gestor-notary" \
    --key "/ruta/AuthKey_XXXXXXXXXX.p8" \
    --key-id "XXXXXXXXXX" \
    --issuer "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
```

`.p8`, *Key ID* e *Issuer ID* se generan en
[App Store Connect → Users and Access → Integrations → App Store Connect API](https://appstoreconnect.apple.com/access/integrations/api).
El `.p8` **solo se descarga una vez**: guárdalo bien.

Comprueba que quedó bien: `xcrun notarytool history --keychain-profile "gestor-notary"`

### Ejecutar

Desde la raíz del repositorio:

```bash
export DEV_ID_APP="Developer ID Application: Nombre Apellidos (TEAMID)"
export AC_PROFILE="gestor-notary"   # el mismo nombre que usaste en store-credentials
bash macos/build_app.sh
```

El script hace, en orden: venv de build → `py2app` → `codesign` con Hardened
Runtime y `macos/entitlements.plist` → `notarytool submit --wait` → `stapler
staple` → DMG → firma + notarización + staple del DMG.

Salida: **`dist/GestorDeCorreos.dmg`** (firmado, notarizado, *stapled*).

### Verificar en otro Mac

```bash
spctl -a -vvv -t open --context context:primary-signature "/Applications/Gestor de Correos.app"
xcrun stapler validate "/Applications/Gestor de Correos.app"
```

---

## Dónde viven los datos en la `.app` instalada

El bundle es de solo lectura y firmado, así que **todo el estado escribible** va a:

```
~/Library/Application Support/GestorDeCorreos/
├── credentials.json      ← lo pones tú (OAuth Desktop de Google Cloud)
├── token.json            ← lo crea la app tras el primer login
├── delete_token.json     ← solo si activas el borrado permanente
├── app_state.json        ← fuentes, reglas, ocultos
├── exports/              ← .eml y .zip exportados
└── .env                  ← opcional (HOST/PORT/AI_*), mismo formato que .env.example
```

Primer uso:

```bash
mkdir -p ~/Library/Application\ Support/GestorDeCorreos
cp /ruta/a/credentials.json ~/Library/Application\ Support/GestorDeCorreos/
```

Override para pruebas: `GESTOR_DATA_DIR=/otra/carpeta` fuerza esa carpeta en
cualquier modo (ver `paths.py`).

---

## Solución de problemas

| Síntoma | Causa / arreglo |
|---|---|
| `error: externally-managed-environment` al hacer `pip install` | Estás usando el Python de Homebrew sin venv. Crea `.venv` (ver *Prueba rápida*). Nunca `--break-system-packages`. |
| `py2app` termina pero el `.app` no arranca / falta `Python` | El `python3` del build no es *framework build*. Relanza con `PYTHON=/ruta/al/python.org/python3 bash macos/build_app.sh`. |
| `notarytool`: *"could not find keychain profile"* | El `AC_PROFILE` que exportaste no coincide con el nombre que diste en `store-credentials`, o nunca lo creaste. Lista lo que hay: `security find-generic-password -s 'com.apple.gke.notary.tool'` o repite `xcrun notarytool store-credentials "<nombre>"`. |
| `codesign`: *"no identity found"* | `DEV_ID_APP` mal escrito o falta el certificado. `security find-identity -v -p codesigning` y copia la línea exacta entre comillas. |
| Notarización `Invalid`: *"binary is not signed" / "no secure timestamp"* en muchos `.so` | `codesign --deep` no firma los binarios anidados. `build_app.sh` los firma uno a uno (inside-out) antes que el bundle. Si añades dependencias con binarios nuevos, no hay que tocar nada: el `find` los cubre. |
| Notarización `Invalid` en `google/_upb/_message.abi3.so` dentro de `python3XX.zip` | Un `.so` dentro del zip no se puede firmar. `build_app.sh` crea `google/__init__.py` en el build-venv y `setup.py` mete `google` en `packages` para copiarlo suelto. |
| `py2app` → `ImportError: No module named 'google'` en `collect_packagedirs` | El paso 2/9 de `build_app.sh` (crear `google/__init__.py`) no se ejecutó o el build-venv es viejo. Borra `build-venv/` y relanza. |
| `py2app` no encuentra otro módulo | Añádelo a `includes` en `macos/setup.py`. Si tiene data files (JSON, plantillas) o binarios, a `packages`. |
| "app is damaged and can't be opened" | Falta staple o la notarización no terminó. Revisa `xcrun notarytool log <id> --keychain-profile "$AC_PROFILE"`. |
| Gatekeeper bloquea al abrir | `spctl` arriba debe decir `accepted`. Si no, la firma o el staple fallaron. |
| La ventana abre en blanco | El servidor no respondió a `/api/status` en 15 s; ejecuta `python3 macos/app_main.py` desde Terminal para ver el error. |
| OAuth no vuelve | El `redirect_uri` de bucle local (`http://localhost`) debe seguir registrado en el cliente OAuth de Google Cloud. No cambia respecto a la app web. |
| Doble instancia / puerto | La app elige un puerto libre efímero; no choca con `server.py` en 8765. |

## Limitaciones conocidas (v1)

- Abrir un `.eml` desde el Finder funciona en el **primer** lanzamiento (argv).
  El `AppleEvent odoc` para una app ya abierta se añadirá después.
- Sin App Sandbox (no hace falta para Developer ID). El hito App Store lo añade.
