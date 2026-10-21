# Publicar en la Mac App Store (Fase 35, ADR-015)

La variante de la Mac App Store sale del **mismo código** que la app firmada con
Developer ID, con `macos/build_mas.sh` en vez de `macos/build_app.sh`. Esta guía
reúne todo lo que hay que hacer, en orden: lo que hace el script y lo que solo
puedes hacer tú en Apple y en Google.

## Qué cambia respecto a la app de Developer ID

| | Developer ID (`build_app.sh`) | Mac App Store (`build_mas.sh`) |
|---|---|---|
| Distribución | DMG + GitHub Releases | Mac App Store (TestFlight para probar) |
| Actualizaciones | Sparkle 2 (y `latest.json` para las 1.2.x) | Las hace la tienda: sin Sparkle, sin menú ni botón ⟳ |
| Aislamiento | Hardened Runtime | **App Sandbox** (sin Hardened Runtime) |
| Datos | `~/Library/Application Support/GestorDeCorreos/` | `~/Library/Containers/com.edefrutos.gestorcorreos/Data/Library/Application Support/GestorDeCorreos/` |
| `credentials.json` | Copiado a mano o importado | Importado (🛠 Configuración) o incluido en la build (`MAS_OAUTH_CLIENT`) |
| Carpeta de respaldo | Ruta libre | Elegida con **📁 Elegir…**; se recuerda con un *security-scoped bookmark* |
| Firma | Developer ID Application + notarización | Apple Distribution + perfil «Mac App Store Connect»; `.pkg` con Mac Installer Distribution |
| Arquitectura | Solo Apple Silicon (arm64) | Solo Apple Silicon (arm64) |

Las dos son solo para Apple Silicon: cryptography ya no publica ruedas x86_64
para macOS, así que `macos/thin_bundle.py` quita la parte Intel de todos los
binarios (en un Mac Intel, macOS avisa de que la app no es compatible).

Las dos variantes comparten el identificador `com.edefrutos.gestorcorreos`. No
instales las dos a la vez en `/Applications`: la tienda no instala encima de una
copia que no sea suya. Los datos **no pasan** de una a otra (el contenedor de
App Sandbox es otra carpeta); si quieres conservar fuentes y reglas, copia
`app_state.json` y `settings.json` a la carpeta del contenedor (la carpeta de
respaldo hay que volver a elegirla con **📁 Elegir…**).

## 0. Probar el sandbox en tu Mac (sin cuenta de App Store Connect)

```bash
git checkout main && git pull
MAS_LOCAL=1 PYTHON=/usr/local/bin/python3.12 bash macos/build_mas.sh
open "dist-mas/Gestor de Correos.app"
```

`MAS_LOCAL=1` firma con tu `DEV_ID_APP` (el de `macos/build.env`) y los mismos
entitlements de App Sandbox, sin perfil ni `.pkg`. Sirve para comprobar que la
app funciona aislada antes de tocar App Store Connect. Lista de pruebas:
`TESTING_HUMANO.md` §10.

Cierra antes la app de Developer ID: las dos usan el mismo identificador.

## 1. Apple: certificados, App ID y perfil

En [developer.apple.com/account](https://developer.apple.com/account) (o Xcode →
Settings → Accounts → Manage Certificates):

1. **Certificados** (Certificates → +):
   - **Apple Distribution** — firma la app.
   - **Mac Installer Distribution** — firma el `.pkg`. En el llavero aparece
     como `3rd Party Mac Developer Installer: … (V29BTBRY6G)`.

   Comprueba los nombres exactos con:
   ```bash
   security find-identity -v | grep -E "Apple Distribution|3rd Party Mac Developer Installer"
   ```
2. **App ID** (Identifiers → +, App IDs → App): bundle ID explícito
   `com.edefrutos.gestorcorreos`, plataforma macOS, sin capacidades extra. Si
   ya existe, úsalo.
3. **Perfil** (Profiles → +): Distribution → **Mac App Store Connect** → el App ID
   anterior → el certificado Apple Distribution. Descárgalo y guárdalo fuera del
   repo, p. ej. `~/.config/gestor-correos/GestorDeCorreos_MAS.provisionprofile`.
4. Añade a `macos/build.env`:
   ```bash
   MAS_APP_IDENTITY="Apple Distribution: Nombre (V29BTBRY6G)"
   MAS_INSTALLER_IDENTITY="3rd Party Mac Developer Installer: Nombre (V29BTBRY6G)"
   MAS_PROFILE="$HOME/.config/gestor-correos/GestorDeCorreos_MAS.provisionprofile"
   ```

## 2. Google: cliente OAuth y pantalla de consentimiento

La tienda la usarán personas que no tienen un proyecto de Google Cloud, así que
la build de la tienda debería llevar **su propio cliente OAuth**.

1. En [console.cloud.google.com](https://console.cloud.google.com), un proyecto
   para la app publicada (mejor uno distinto del que usas a diario), con la
   **Gmail API** activada.
2. **Pantalla de consentimiento OAuth** (Google Auth Platform → Branding):
   nombre «Gestor de Correos», correo de asistencia, logotipo, página principal
   y **política de privacidad**: `docs/PRIVACY.md` publicada, p. ej.
   `https://github.com/edfrutos/gestor-correos-gmail/blob/main/docs/PRIVACY.md`.
3. **Permisos** (Data Access): `https://www.googleapis.com/auth/gmail.modify`.
   El borrado permanente usa además `https://mail.google.com/`; si no lo vas a
   ofrecer a los usuarios de la tienda, no lo declares (es el permiso que más
   cuesta verificar) y deja `ENABLE_PERMANENT_DELETE` sin activar.
4. **Cliente** (Clients → Create client): tipo **App de escritorio**. Descarga el
   JSON y apúntalo en `macos/build.env` (fuera del repo):
   ```bash
   MAS_OAUTH_CLIENT="$HOME/.config/gestor-correos/oauth_client_mas.json"
   ```
   El secreto de un cliente de escritorio no es confidencial para Google (va
   dentro de cada app instalada), pero no lo subas al repo.
5. **Estado de publicación:**
   - **Testing**: solo los usuarios de prueba que añadas (máx. 100) pueden
     autorizar, y su autorización caduca a los 7 días. Basta para TestFlight y
     para la revisión de Apple si añades la cuenta de demostración.
   - **In production** con `gmail.modify` (permiso *restringido*) exige la
     **verificación de Google**: revisión de marca y de la política de
     privacidad, vídeo del flujo de autorización y una **evaluación de
     seguridad CASA** anual por un evaluador autorizado (de pago). Sin ella,
     los usuarios ven «Google no ha verificado esta aplicación» y hay un límite
     de 100 usuarios.

Sin `MAS_OAUTH_CLIENT` la app funciona igual, pero cada usuario tiene que crear
su propio cliente e importarlo (🛠 Configuración → **📄 Importar
credentials.json…**). Es lo que hace hoy la app de Developer ID, pero es poco
viable para el público de la tienda y para la revisión.

## 3. App Store Connect: la ficha

En [appstoreconnect.apple.com](https://appstoreconnect.apple.com) → Apps → + →
**New App**: plataforma macOS, nombre (debe estar libre en la tienda),
idioma principal español, bundle ID `com.edefrutos.gestorcorreos`, SKU libre
(p. ej. `gestor-correos-mac`).

Lo que pide antes de enviar a revisión:

- **Política de privacidad** (URL) y **URL de soporte** (vale la de issues).
- **Privacidad de la app**: el desarrollador no recoge datos (ningún dato llega
  a servidores tuyos). Revisa tú las respuestas: si incluyes un proveedor de IA
  remoto por defecto, o analítica, cambian.
- **Categoría**: Productividad (ya va en `LSApplicationCategoryType`).
- **Capturas**: al menos una de 1280×800, 1440×900, 2560×1600 o 2880×1800.
- **Cifrado**: la app declara `ITSAppUsesNonExemptEncryption = false` (solo
  HTTPS del sistema), así que no pide documentación de exportación.
- **Notas para la revisión** (App Review Information), por ejemplo:
  > Gestor de Correos organiza la cuenta de Gmail del usuario. Para probarla,
  > pulsa «Buscar» con cualquier término: se abre en el navegador el login de
  > Google; usa la cuenta de demostración indicada (es usuario de prueba de
  > nuestro proyecto OAuth). La app sirve su interfaz desde un servidor
  > interno en 127.0.0.1 que solo atiende a su propia ventana; no descarga
  > ni ejecuta código.

  Y en *Sign-in information*, una cuenta de Gmail de demostración con algunos
  correos, añadida como usuario de prueba en el paso 2.5.

## 4. Compilar, subir y probar con TestFlight

```bash
PYTHON=/usr/local/bin/python3.12 bash macos/build_mas.sh
```

Genera `dist-mas/GestorDeCorreos-<VERSION>-<BUILD>.pkg`. Para subirlo, usa la
app **Transporter** (gratis en la Mac App Store): arrastra el `.pkg` y pulsa
Entregar. También puedes subirlo con `xcrun altool --upload-app` y una clave de
la API de App Store Connect (el script imprime el comando). Con `MAS_API_KEY` y
`MAS_API_ISSUER` definidos, el script además lo valida antes.

Cada subida necesita un **número de build nuevo** para la misma versión:
`MAS_BUILD_NUMBER=2 PYTHON=… bash macos/build_mas.sh` (por defecto es `VERSION`).

Cuando App Store Connect termine de procesarlo (minutos), en **TestFlight →
Internal Testing** añádete como probador e instala la build con la app TestFlight
en tu Mac. Haz ahí las pruebas de `TESTING_HUMANO.md` §10 y, si van bien,
**Enviar a revisión** desde la versión de la ficha.

## Problemas frecuentes al subir

| Error | Causa / arreglo |
|---|---|
| `ITMS-90296: App sandbox not enabled` | Algún ejecutable no lleva `com.apple.security.app-sandbox`. `build_mas.sh` firma los anidados con `entitlements-mas-inherit.plist`; si añades un binario nuevo fuera de `Contents/MacOS`, fírmalo igual. |
| `ITMS-90287: Invalid Code Signing Entitlements` | `application-identifier`/`team-identifier` no coinciden con el perfil. El script lo comprueba antes de firmar; revisa que el perfil sea del App ID correcto. |
| `ITMS-90889` / perfil de desarrollo | Hace falta un perfil **Mac App Store Connect** (distribución). El script se para si el perfil lista dispositivos. |
| `ITMS-4238: Redundant Binary Upload` | Ese `CFBundleVersion` ya se subió: vuelve a compilar con otro `MAS_BUILD_NUMBER`. |
| `ITMS-90338: Non-public API usage` | Aviso típico de apps con PyObjC (selectores con nombres que coinciden con API privadas). Si App Review lo rechaza, anota el selector y lo revisamos. |
| La app abre y se cierra al instante (TestFlight) | Mira *Consola → Informes de fallos*. Si aparece `deny(1)` del sandbox, falta un entitlement o un acceso a archivo: pásame el log. |

## Riesgos de la revisión de Apple

- **4.2 (funcionalidad mínima / «envoltorio web»)**: la interfaz es HTML, pero
  todo corre en local (servidor en 127.0.0.1 y lógica en Python) y la app
  integra funciones del sistema (abrir `.eml` desde el Finder, selectores
  nativos de archivos y carpetas). Conviene explicarlo en las notas.
- **5.1.1 (datos y privacidad)**: hace falta la política de privacidad y que el
  login de Google no sea obligatorio para *abrir* la app (no lo es: sin cuenta
  se pueden abrir `.eml`).
- **2.5.2 (código descargado)**: no aplica; sin Sparkle ni updater propio en
  esta variante.

Si App Review rechaza la variante py2app por el «envoltorio web», el plan B es
el de la versión original de la Fase 35: un shell nativo en Swift con WKWebView
que lance el mismo backend en Python.
