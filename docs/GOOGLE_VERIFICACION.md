# Verificación de Google (permiso restringido `gmail.modify`)

Sin esta verificación, solo los usuarios de prueba del proyecto pueden iniciar
sesión. Ver ADR-016. Los textos para Google están en inglés, listos para pegar.

## Orden de los pasos

| # | Paso | Dónde | Estado |
|---|------|-------|--------|
| 1 | Retirar la app de la venta | App Store Connect → Precio y disponibilidad | Hecho el 2026-11-04 |
| 2 | Publicar `docs/site/` (`index.html`, `privacy.html` y `site.css`) en `https://gcorreos.efjdev.com/`. Es web estática: no hace falta WordPress | Hosting | Hecho; la web coincide con `docs/site/` |
| 3 | Verificar `efjdev.com` en Search Console (propiedad de dominio, con un registro TXT en el DNS), con una cuenta propietaria del dominio y del proyecto de Google | Search Console | Hecho |
| 4 | Compilar la v1.4.1 y subirla a TestFlight (sin IA remota ni borrado permanente, con la Papelera) | `macos/build_mas.sh` con un `MAS_BUILD_NUMBER` mayor que cualquiera ya subido | Build 7 (`4a5b717`, visor de `.eml` aislado) subida el 2026-11-08, en proceso en TestFlight. Es la que debe grabarse y enviarse a App Review; la build 6 no sirve |
| 5 | Completar la marca: nombre «Gestor de Correos», logotipo, correo de asistencia, página principal `https://gcorreos.efjdev.com/`, política `https://gcorreos.efjdev.com/privacy.html` y dominio autorizado `efjdev.com` | Google Auth Platform → Información de la marca | Hecho |
| 6 | Declarar **solo** `gmail.modify`; quitar `https://mail.google.com/` si estuviera | Google Auth Platform → Acceso a los datos | Hecho |
| 7 | Grabar el vídeo con la build del paso 4 y subirlo a YouTube como oculto | Guion más abajo | Pendiente: cuando la build 7 esté disponible en TestFlight y pase las comprobaciones |
| 8 | Pulsar «Publicar app» y enviar a verificación con los textos de abajo | Google Auth Platform → Público y Centro de verificación | Pendiente |
| 9 | Responder a Google y, si la exige, hacer la evaluación CASA | Correo de Google | Pendiente |
| 10 | Con la verificación aprobada, enviar la v1.4.1 a App Review, volver a poner la app a la venta y decidir si se activan EE. UU. y Canadá | App Store Connect | Pendiente |

Hasta el paso 10, la app no debe volver a la venta: el público no podría iniciar
sesión.

## Evaluación CASA: qué sabemos

Es la principal incógnita de coste. Según la [guía de Google](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification),
la evaluación afecta a las apps que pueden acceder a los datos *from or through a
third-party server*, y añade: *If you store or transmit restricted scope data on
servers, then you need to complete a security assessment*. La app de la tienda no
usa servidores propios.

Pero ninguna página recoge una exención expresa para apps locales, y la
[política de datos](https://developers.google.com/terms/api-services-user-data-policy)
habla de una evaluación anual sin hacer esa distinción. **Lo decide Google**: por
eso la justificación lo plantea de forma explícita. Si la exige, hay que valorar
de nuevo si compensa, porque es anual y de pago.

## Riesgos que conviene resolver antes de enviar

- **La palabra «Gmail» en el nombre.** Decidido: la app se llama «Gestor de Correos»
  en la ficha de la v1.4.1 y en la pantalla de consentimiento, porque Google limita
  el uso de sus marcas sin permiso. App Store Connect confirmará si el nombre está
  libre al guardarlo; la búsqueda pública de la tienda no lo garantiza. Alternativa
  si está cogido: «GCorreos».
- **Nombres coincidentes.** La pantalla de consentimiento, la página principal y
  la app deben mostrar el mismo nombre.
- **Web pública.** La página principal debe ser accesible sin iniciar sesión y
  explicar la app. Una ficha de tienda no vale como página principal según Google
  (lo dice expresamente de Google Play), y la política debe estar en el mismo
  dominio.

## Justificación para Google

### App description

```text
Gestor de Correos is a native macOS application, distributed through the Mac App Store, that helps people organize their own Gmail account, focusing on technical notifications such as hosting, domain, SSL certificate, security and billing notices. It searches the user's mail, classifies each message by category and severity on the user's Mac, and lets the user archive, label, move to the Gmail Trash and export messages.
```

### Scope justification: gmail.modify

```text
Gestor de Correos requests https://www.googleapis.com/auth/gmail.modify and no other Gmail scope.

Features that depend on this scope:
- Search and display: users.messages.list, users.messages.get, users.threads.list, users.threads.get and users.messages.attachments.get show the messages the user searches for, their content and their attachments, and let the user export them to .eml or .zip files on their own Mac.
- Labels: users.labels.list and users.labels.create let the user pick or create a label.
- Archive and label: users.messages.batchModify removes the INBOX label or adds a label, only on messages the user selected, after the user confirms the action.
- Move to Trash: users.messages.trash moves a message to the Gmail Trash, only for messages the user has hidden in the app and selected, after the user confirms the action. Gmail keeps them for 30 days, and the user can recover them from Gmail during that time.

Why a narrower scope is not sufficient: gmail.readonly and gmail.metadata cannot archive, label or trash messages, which are core features; gmail.metadata also cannot read the message content needed to display and classify messages and to export them; gmail.labels cannot read messages. The app never sends or drafts email and never permanently deletes it.
```

### Data handling and security assessment

```text
Gestor de Correos has no backend. The developer operates no server that receives, stores or can access Google user data, and the app contains no analytics, advertising or tracking.

Data flow: the app calls the Gmail API directly from the user's Mac over HTTPS. Message content is processed in memory on the user's device. The OAuth token and the user's settings are stored locally inside the app's macOS App Sandbox container, with permissions restricted to the user. Exported files are written inside that container and, only if the user chooses a backup folder, copied to that folder on their own Mac.

Network: the app's interface is served to its own window from a loopback server on 127.0.0.1, and sign-in uses the OAuth loopback redirect for desktop apps. Neither is reachable from other machines.

Optional AI: the Mac App Store build only accepts a local model running on the user's own Mac (for example, Ollama on localhost). Remote AI providers are refused by the application, so Google user data does not leave the device.

Limited Use: the app uses Google user data only to provide the user-facing features described above. It does not sell or transfer the data, use it for advertising, or use it to train AI models, and no human can read it, because the developer never receives it.

Because restricted scope data is not stored on, transmitted to or accessed from or through any server of ours or of a third party, we understand that the security assessment does not apply. Please confirm whether this is correct or tell us what you need in order to assess it. The source code is available at https://github.com/edfrutos/gestor-correos-gmail.
```

## Comprobaciones en la v1.4.1 de TestFlight

Con la build 7 instalada desde TestFlight, antes de grabar el vídeo:

- [ ] La ventana «Ocultos locales» no muestra la sección «Eliminación permanente» y
  su texto inicial no habla de borrar en Gmail.
- [ ] «Mover a la Papelera» pide confirmación, el mensaje aparece en la Papelera de
  Gmail y desaparece de «Ocultos locales». Desde Gmail se puede recuperar.
- [ ] 🛠 Configuración no ofrece importar `credentials.json` y, en la IA, propone
  `llama3` y `ollama`, sin mencionar `gpt-4o-mini`, `sk-…` ni `.env`.
- [ ] 🛠 Configuración rechaza `https://api.openai.com/v1` con «IA remota no
  disponible», y también `http://localhost:11434/v1` con un modelo `…:cloud`.
- [ ] Un modelo local en `http://localhost:11434/v1` sigue funcionando, si tienes
  Ollama.
- [ ] La cuenta de demostración busca, etiqueta, archiva y exporta sin errores.
- [ ] Con la app abierta, revocar el acceso en `myaccount.google.com/permissions`:
  la siguiente búsqueda avisa de que la autorización expiró o fue revocada, y la
  posterior abre Google sin reiniciar la app.
- [ ] Abrir en el visor un `.eml` con imágenes remotas: el texto se lee, las imágenes
  remotas no se cargan y un enlace del correo se abre en el navegador.
- [ ] La ficha de App Store Connect indica el idioma español tras publicarse; hasta
  entonces no se puede comprobar.

## Capturas de la ficha

Rehechas con la 1.4.1 y subidas el 2026-11-05. `capturas-mas/` (fuera del repo)
conserva `5-reglas-ia` y `6-ocultos`, de la versión anterior: no deben subirse.
Las capturas no deben mostrar direcciones personales.

## Guion del vídeo

Con la build de TestFlight (paso 4) y la sesión de Google cerrada, en inglés o con subtítulos en inglés. Debe
mostrar de principio a fin cómo el usuario inicia y concede el acceso. Conviene
que se vea el identificador de cliente en la barra de direcciones.

1. Mostrar el Mac y abrir **Gestor de Correos**, con su nombre visible.
2. Pulsar **Buscar en Gmail**. Se abre Google en el navegador.
3. Ampliar la **barra de direcciones** para que se lea el `client_id`, y que
   coincida con el del proyecto enviado.
4. Elegir la cuenta y mostrar la pantalla de consentimiento completa, con el
   nombre de la app y el permiso solicitado. Conceder el acceso.
5. Volver a la app. **Buscar y leer:** buscar por remitente, abrir un mensaje y un
   adjunto.
6. **Clasificar:** enseñar las categorías y la severidad, y explicar que se
   calculan en el Mac.
7. **Etiquetar:** seleccionar mensajes, crear o elegir una etiqueta y confirmar.
   Enseñar el resultado en Gmail.
8. **Archivar:** seleccionar mensajes, confirmar y enseñar en Gmail que han salido
   de la bandeja de entrada.
9. **Mover a la Papelera:** ocultar un mensaje, abrir «Ocultos locales», seleccionarlo,
   mover a la Papelera y confirmar. Enseñar el mensaje en la Papelera de Gmail.
10. **Exportar:** exportar un mensaje a `.eml` y enseñar el archivo en el Finder (por
    defecto queda dentro del contenedor de la app; con carpeta de respaldo, también
    en ella: es la forma más sencilla de enseñarlo).
11. **Datos locales y revocación:** explicar que nada llega al desarrollador y
    enseñar cómo revocar el acceso en `myaccount.google.com/permissions`.
