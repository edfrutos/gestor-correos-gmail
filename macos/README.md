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

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-macos.txt
.venv/bin/python macos/app_main.py            # abre la ventana
.venv/bin/python macos/app_main.py correo.eml # abre un .eml en el visor
```

Datos escribibles en este modo (ejecutado desde el código fuente): la **carpeta
del proyecto**, como siempre. Coloca ahí `credentials.json`.

---

## Build firmado + notarizado (produce el DMG)

### Requisitos en el Mac

- **Xcode Command Line Tools**: `xcode-select --install`
- **Python 3.11+** (el del sistema o Homebrew).
- **Cuenta Apple Developer** y certificado **Developer ID Application** instalado
  en el llavero. Compruébalo: `security find-identity -v -p codesigning`
- **Perfil de notarytool** guardado una sola vez:

  ```bash
  xcrun notarytool store-credentials "gestor-notary" \
      --apple-id "TU_APPLE_ID" --team-id "TEAMID" \
      --password "APP-SPECIFIC-PASSWORD"   # contraseña de app en appleid.apple.com
  ```

### Ejecutar

Desde la raíz del repositorio:

```bash
export DEV_ID_APP="Developer ID Application: Nombre Apellidos (TEAMID)"
export AC_PROFILE="gestor-notary"
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
| `py2app` no encuentra `googleapiclient` / `google` | Ya están en `packages` de `macos/setup.py`; si aparece otro módulo, añádelo a `includes`. |
| "app is damaged and can't be opened" | Falta staple o la notarización no terminó. Revisa `xcrun notarytool log <id> --keychain-profile "$AC_PROFILE"`. |
| Gatekeeper bloquea al abrir | `spctl` arriba debe decir `accepted`. Si no, la firma o el staple fallaron. |
| La ventana abre en blanco | El servidor no respondió a `/api/status` en 15 s; ejecuta `python3 macos/app_main.py` desde Terminal para ver el error. |
| OAuth no vuelve | El `redirect_uri` de bucle local (`http://localhost`) debe seguir registrado en el cliente OAuth de Google Cloud. No cambia respecto a la app web. |
| Doble instancia / puerto | La app elige un puerto libre efímero; no choca con `server.py` en 8765. |

## Limitaciones conocidas (v1)

- Abrir un `.eml` desde el Finder funciona en el **primer** lanzamiento (argv).
  El `AppleEvent odoc` para una app ya abierta se añadirá después.
- Sin App Sandbox (no hace falta para Developer ID). El hito App Store lo añade.
