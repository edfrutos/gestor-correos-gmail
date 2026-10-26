# Ficha de App Store Connect — textos listos para pegar

Complementa el §3 de `MAC_APP_STORE.md`. Límites de Apple entre paréntesis.

## Información de la app

| Campo | Valor |
|---|---|
| Nombre (30) | `Gestor de Correos` |
| Subtítulo (30) | `Avisos técnicos de Gmail` |
| Categoría principal | Productividad |
| Categoría secundaria | Utilidades |
| URL de la política de privacidad | `https://github.com/edfrutos/gestor-correos-gmail/blob/main/docs/PRIVACY.md` |
| URL de soporte | `https://github.com/edfrutos/gestor-correos-gmail/issues` |
| Copyright | `2026 EDF Developer` |
| Precio | Gratis (o el que decidas) |

## Texto promocional (170)

```
Encuentra en segundos los avisos que importan de tu Gmail: certificados, facturación, renovaciones, seguridad y copias de seguridad. Todo se procesa en tu Mac.
```

## Palabras clave (100, separadas por comas, sin espacios)

```
gmail,correo,email,avisos,servidor,ssl,dominio,factura,alertas,devops,hosting,etiquetas,exportar,eml
```

## Descripción (4000)

```
Gestor de Correos convierte los correos técnicos dispersos en tu Gmail —avisos de hosting, dominios, certificados SSL, facturación, vulnerabilidades o copias de seguridad— en una vista ordenada y accionable.

QUÉ HACE
• Busca en tu Gmail por remitente, texto y fechas, con fuentes predefinidas (Amazon/AWS, Let's Encrypt, GitHub, Stripe, Cloudflare, PayPal…) y las que añadas tú.
• Clasifica cada correo por categoría y severidad para que veas primero lo que requiere atención.
• Agrupa los avisos por proveedor y detecta los asuntos que se repiten.
• Reglas personalizables con palabras clave para tus propios proveedores, con sugerencias por IA si la activas.
• Resúmenes de los últimos 7 o 30 días y tendencias.
• Archiva y etiqueta en lote, con confirmación; oculta lo que ya revisaste.
• Exporta mensajes completos a .eml o .zip y abre archivos .eml desde el Finder, incluso sin cuenta conectada.
• Resúmenes con IA opcionales: local o con el proveedor que tú configures, siempre con aviso previo.

PRIVACIDAD
• Tus correos van directamente de Google a tu Mac. El desarrollador no recibe ningún dato: sin servidores propios, sin analítica, sin publicidad.
• La app se conecta a Gmail con la autorización oficial de Google y puedes revocarla cuando quieras.
• Todo lo que guarda (preferencias, reglas, exportaciones) se queda en tu Mac.

Requiere una cuenta de Gmail o Google Workspace.
```

## Novedades de esta versión (solo a partir de la segunda versión publicada)

```
Primera versión en la Mac App Store.
```

## Privacidad de la app (cuestionario)

- **¿Recoges datos de esta app?** → **No, no recogemos datos.**
  Es correcto mientras no haya analítica ni un proveedor de IA remoto activado
  por defecto: los correos viajan de Google al Mac y nunca a servidores del
  desarrollador. Si eso cambia, hay que rehacer el cuestionario.

## Información para la revisión (App Review Information)

**Sign-in information:** la cuenta de Gmail de demostración (usuario de prueba
del proyecto OAuth de la tienda) y su contraseña. Marca «Sign-in required».

**Notes:**

```
Gestor de Correos organizes the user's own Gmail account, focusing on technical notifications (hosting, domains, SSL certificates, billing).

How to test:
1. Open the app. Without signing in you can already open .eml files (Exportaciones locales → "Abrir archivo .eml externo…").
2. Click "Buscar en Gmail" (any sender or text, or just the date range). Google's sign-in page opens in the browser; use the demo account provided. It is a test user of our OAuth project, so Google may show an "unverified app" notice: choose Continue.
3. Results are classified by category and severity; open any message to see its content and attachments.

Architecture: the interface is HTML, but all logic runs locally in Python inside the app bundle. It is served from an internal server on 127.0.0.1 that only answers its own window. The app does not download or execute code, has no self-updater in this version (updates come from the Mac App Store), and sends no data to the developer. It uses native macOS features: file and folder pickers, opening .eml files from the Finder.

Network entitlements: com.apple.security.network.server is required because the app listens on the loopback interface only: (1) the app's own window (WKWebView) loads its interface from an HTTP server bound to 127.0.0.1 on a random free port, started in-process at launch; (2) Google sign-in uses the OAuth "loopback redirect" flow required by Google for desktop apps, which briefly listens on 127.0.0.1 to receive the authorization code. Nothing is reachable from other machines. com.apple.security.network.client is used for the Gmail API and Google OAuth.

Privacy policy: https://github.com/edfrutos/gestor-correos-gmail/blob/main/docs/PRIVACY.md
```

## Capturas

Mínimo una a 1280×800, 1440×900, 2560×1600 o 2880×1800 (16:10), hasta 10.
Recomendado, hechas **con la build de la tienda** (TestFlight: no muestra el
botón «⟳ Actualizaciones») y la cuenta de demostración con correos cargados:

1. Resultados de una búsqueda con categorías y severidades.
2. Un correo abierto en el modal.
3. Resumen de 30 días / tendencias.
4. Reglas personalizadas.

Para pasarlas a 2880×1800 sin deformarlas, centradas sobre fondo oscuro:

```bash
python3 - captura.png <<'EOF'
import sys
from PIL import Image
src = Image.open(sys.argv[1]).convert("RGB")
W, H = 2880, 1800
s = min((W - 160) / src.width, (H - 120) / src.height)
im = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
c = Image.new("RGB", (W, H), (13, 17, 23))
c.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
c.save(sys.argv[1].rsplit(".", 1)[0] + "-2880x1800.png")
EOF
```
