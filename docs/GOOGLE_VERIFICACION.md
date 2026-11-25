# Verificación de Google (permiso restringido `gmail.modify`)

Sin esta verificación, solo los usuarios de prueba del proyecto pueden iniciar
sesión. Ver ADR-016. Los textos para Google están en inglés, listos para pegar.

## Orden de los pasos

| # | Paso | Dónde | Estado |
|---|------|-------|--------|
| 1 | Retirar la app de la venta | App Store Connect → Precio y disponibilidad | Hecho el 2026-11-04. El 2026-11-19 la v1.4.0 volvió a estar a la venta, también en EE. UU.; el usuario decide mantenerla (ver nota bajo la tabla) |
| 2 | Publicar `docs/site/` (`index.html`, `privacy.html` y `site.css`) en `https://gcorreos.efjdev.com/`. Es web estática: no hace falta WordPress | Hosting | Hecho; la web coincide con `docs/site/` |
| 3 | Verificar `efjdev.com` en Search Console (propiedad de dominio, con un registro TXT en el DNS), con una cuenta propietaria del dominio y del proyecto de Google | Search Console | Hecho |
| 4 | Compilar la v1.4.1 y subirla a TestFlight (sin IA remota ni borrado permanente, con la Papelera) | `macos/build_mas.sh` con un `MAS_BUILD_NUMBER` mayor que cualquiera ya subido | Hecho: build 8 subida a TestFlight el 2026-11-15. Añade a la 7 (visor de `.eml` aislado) el cierre de los modales (PR #47) y las sugerencias IA con modelos locales (PR #48). Es la que debe grabarse y enviarse a App Review; las builds 6 y 7 no sirven |
| 5 | Completar la marca: nombre «Gestor de Correos», logotipo, correo de asistencia, página principal `https://gcorreos.efjdev.com/`, política `https://gcorreos.efjdev.com/privacy.html` y dominio autorizado `efjdev.com` | Google Auth Platform → Información de la marca | Hecho |
| 6 | Declarar **solo** `gmail.modify`; quitar `https://mail.google.com/` si estuviera | Google Auth Platform → Acceso a los datos | Hecho |
| 7 | Grabar el vídeo con la build del paso 4 y subirlo a YouTube como oculto | Guion más abajo | Hecho el 2026-11-15: grabado con la build 8 y publicado en YouTube. Rehecho el 2026-11-22 con la v1.4.2 de descarga directa (ver la nota del 2026-11-22); el enlace no se guarda aquí |
| 8 | Pulsar «Publicar app» (a producción). Hasta la verificación, quien inicie sesión verá el aviso de app no verificada, con un máximo de 100 usuarios. Cuando se hizo no importaba porque la app no estaba a la venta; desde el 2026-11-19 sí lo está | Google Auth Platform → Público | Hecho el 2026-11-15 |
| 9 | Verificar la marca. Google revisa la página principal, la política y el dominio verificado en Search Console; tarda unos días laborables y no necesita vídeo. Se puede hacer mientras se graba el vídeo | Google Auth Platform → Información de la marca | Hecho: marca verificada (Centro de verificación, 2026-11-15) |
| 10 | Con la marca verificada se activa «Prepare for verification»: enviar la verificación del acceso a los datos con los textos de abajo y el vídeo | Google Auth Platform → Centro de verificación | Hecho: enviada el 2026-11-15; el acceso a los datos está en revisión. La consola mostró «No se pudo enviar tu app» (seguimiento `c125087734537070`), pero el envío quedó registrado |
| 11 | Responder a Google y, si la exige, hacer la evaluación CASA | Correo de Google | En curso: el 2026-11-18 llegó la lista de comprobación estándar («You must reply to this email…») y ese mismo día se respondió con el texto de «Respuesta a la lista de comprobación», con el enlace del vídeo revisado en el punto 2. Ya estaban publicadas la política ampliada y la build 8 en TestFlight con enlace público. El 2026-11-18 (20:15 UTC) Apple aprobó la build 1.4.1 (8) para la beta externa de TestFlight: el enlace público que recibe el revisor ya funciona. El 2026-11-20 el Centro de verificación mostraba 2 de 7 etapas aprobadas (página principal y marca, el 2026-11-15) y la política de privacidad en revisión; faltan funciones de la app, acceso a los datos adecuado, permisos mínimos y requisitos adicionales (donde se decidiría la CASA). Google estima de 4 a 6 semanas desde el envío del 2026-11-15, es decir, hacia el 13–27 de diciembre. Pendiente: la respuesta de Google y si exige la evaluación CASA. 2026-11-22: vídeo nuevo grabado con la v1.4.2 de descarga directa; hay que enviarlo respondiendo al hilo, con el párrafo «Update on distribution» de la nota del 2026-11-22. **2026-11-25: Google exige la evaluación ADA-CASA AL1 antes del 22-02-2027. El usuario decide no hacerla (es de pago y anual); ver la nota del 2026-11-25** |
| 12 | Publicar la descarga directa sin esperar a la verificación | GitHub Releases | Sustituido por la v1.4.3 (nota del 2026-11-25): se publica con el cliente compartido sin verificar y la opción de usar un cliente propio. La v1.4.2 queda como borrador sin publicar |

**2026-11-19 — La v1.4.0 vuelve a estar a la venta.** La API de búsqueda de iTunes
(`lookup?id=6825322977`) la devuelve en ES, GB y US. No hay correo de Apple sobre
ella: los «Ready for Distribution» de ese día son de otras apps (Replacer 1.4.0 y
Extractor URL 2.3). El usuario decide **mantenerla a la venta** mientras Google
responde, sabiendo que:

- quien inicie sesión verá el aviso de app no verificada, y `gmail.modify` está
  limitado a 100 usuarios hasta la verificación;
- la v1.4.0 aún ofrece IA remota y borrado permanente, que la v1.4.1 quita en la
  variante de la tienda (ADR-016), y su «Ocultos locales» todavía habla de borrar
  en Gmail;
- la app pública no coincide con la build 8 que se ha declarado a Google, así que
  conviene publicar la v1.4.1 en cuanto Google la verifique.

**2026-11-22 — Distribución directa con el cliente verificado.** La app se ha
retirado de la Mac App Store y se distribuye como descarga directa (Developer ID +
notarización + Sparkle) desde GitHub Releases. Para que esa descarga use el
cliente OAuth del proyecto en verificación:

- `macos/build_app.sh` acepta `DIRECT_OAUTH_CLIENT` (en `macos/build.env`, el mismo
  JSON que `MAS_OAUTH_CLIENT`) y lo copia a `Contents/Resources/oauth_client.json`
  antes de firmar (PR #62). El paso «3c/9» debe decir «cliente OAuth incluido».
- Con ese cliente incluido, `paths.verified_scope_only()` desactiva el borrado
  permanente (`mail.google.com`) y la IA remota, igual que en la tienda (PR #62).
- La v1.4.2 (PR #63) es la primera build directa con el cliente. La v1.4.1 publicada
  en GitHub se compiló antes del PR #62 y **no** lo lleva.
- El indicador de estado pasa a verde tras la primera búsqueda autorizada (PR #64).
- Quien ya tenga un `credentials.json` propio en
  `~/Library/Application Support/GestorDeCorreos/` sigue usándolo: la app no lo
  sustituye por el incluido. Para probar el cliente del proyecto hay que apartarlo
  (y `token.json`) antes de abrir la app.

Párrafo para Google (respuesta al hilo de verificación):

```text
Update on distribution: Gestor de Correos is no longer distributed through the Mac App Store. It is now distributed as a Developer ID signed and Apple-notarized download from GitHub (version 1.4.2): https://github.com/edfrutos/gestor-correos-gmail/releases/latest. This build requests only https://www.googleapis.com/auth/gmail.modify with this project's OAuth client, and it does not include permanent deletion or remote AI. To install it: download the .dmg, drag Gestor de Correos to Applications, open it and click "Buscar en Gmail" (Search Gmail).
```

Mientras la v1.4.2 siga como borrador, `releases/latest` apunta a la v1.4.1: en ese
caso, quitar el enlace y decir que la build se publicará tras la verificación.

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

### Información adicional (versión de 1000 caracteres)

El cuadro «Información adicional» del Centro de verificación admite 1000 caracteres,
y el texto anterior no cabe. Versión recortada:

```text
Gestor de Correos is a native macOS app (Mac App Store) with no backend. The developer runs no server that receives, stores or can access Google user data; there are no analytics, ads or tracking.

The app calls the Gmail API directly from the user's Mac over HTTPS. Message content is processed in memory on the device. The OAuth token, settings and exported files stay on the user's Mac, inside the app's sandbox container or a folder the user chooses. The optional AI only accepts a local model on the same Mac; remote providers are refused.

Limited Use: data is used only for the user-facing features, never sold, transferred, used for ads or to train AI models. No human can read it.

Since restricted scope data is not stored on, transmitted to or accessed through any server, we understand the security assessment does not apply. Please confirm or tell us what you need.

Source code: https://github.com/edfrutos/gestor-correos-gmail
```

### Cuestionario de verificación

Las cuatro preguntas (uso personal, uso interno, solo desarrollo o pruebas, complemento
SMTP para WordPress) se responden «No». Para enviar hay que marcar dos casillas: que
se cumplen los requisitos y que se entiende que los permisos restringidos exigen la
evaluación CASA, renovada cada año. El formulario no distingue las apps sin servidor.

## Respuesta a la lista de comprobación (2026-11-18)

Google respondió al envío con su lista de comprobación genérica, que pide revisar
cada punto y contestar al mismo correo confirmándolo. Antes de responder:

1. Publicar la `docs/site/privacy.html` actualizada en
   `https://gcorreos.efjdev.com/privacy.html`. La versión anterior no cubría la
   protección ni la conservación de los datos, que la lista exige por separado.
   Hecho el 2026-11-18: la versión publicada coincide con la del repositorio.
2. Revisar el vídeo: en la pantalla de consentimiento debe leerse el permiso
   completo (si Google lo agrupa, desplegarlo con «Mostrar todos los servicios»),
   y en Gmail debe verse el resultado de etiquetar, archivar y mover a la
   Papelera. Si falta algo, grabarlo de nuevo antes de responder.
   Hecho el 2026-11-18: vídeo publicado en YouTube como oculto. Si su enlace no es
   el del envío del 2026-11-15, hay que sustituirlo en el Centro de verificación
   antes de responder. El enlace no se guarda aquí porque el repositorio es público.
3. Esperar a que Apple apruebe la build 8 en la revisión beta y comprobar que el
   enlace público de TestFlight la instala. El revisor de Google la instala con
   ese enlace (ver «Enlace público de TestFlight» más abajo).
   Hecho el 2026-11-18: Apple aprobó la build y el enlace está activo.

Respuesta enviada el 2026-11-18 con el texto de abajo. El punto 2 incluía el
enlace del vídeo revisado, porque en la consola no apareció dónde cambiarlo con
la solicitud en revisión. El correo de Google admite las dos vías.

### Enlace público de TestFlight

- Grupo externo «Revisión de Google», con la build 1.4.1 (8) y un límite de 10
  probadores. Enlace: `https://testflight.apple.com/join/sGAXphFa`. Solo funciona
  cuando Apple aprueba la build en la revisión beta.
- *Sign-in information*: la cuenta de Gmail de demostración, la misma de App Review
  (sin verificación en dos pasos). *What to Test* no lleva datos de la cuenta,
  porque lo ve cualquier grupo con acceso a la build.
- La build caduca a los 90 días de subirse (2026-11-15, hacia el 2027-02-13). Si
  la revisión de Google se alarga, hay que subir otra build y añadirla al grupo.

Texto para responder (en inglés):

```text
Hello,

Thank you for the checklist. We have audited Gestor de Correos (project gestor-de-correo-gmail, 1771725945) against every item. Summary:

1. Scopes. The app requests only https://www.googleapis.com/auth/gmail.modify, the same single scope declared in the Cloud Console. It is used for production, user-facing features only: search and read messages and attachments, label, archive, move to Trash (recoverable for 30 days) and export to .eml/.zip. gmail.readonly and gmail.metadata cannot label, archive or trash; gmail.labels cannot read messages. The app never sends, drafts or permanently deletes email. Note: the public source repository also contains an optional permanent-delete module using https://mail.google.com/; it belongs to a separate self-hosted edition that uses each user's own OAuth client, and it is disabled in code in the Mac App Store build submitted here, which never requests that scope with this project's client.

2. Demo video. The video is unlisted on YouTube. It shows the full OAuth flow with the client ID visible, the consent screen with the requested scope, every feature that uses the scope, and the result of each write action (label, archive, move to Trash) in the user's Gmail account.

3. Live app. The app is currently removed from sale on the Mac App Store and will only be made available again after verification, so no production traffic uses the unverified scope.

4. App access. Sign-in is Google OAuth only: there is no local login, phone verification or payment step. Gestor de Correos is a native macOS app (macOS 12 or later) and is currently not on sale. You can install the exact build shown in the video through this TestFlight public link: https://testflight.apple.com/join/sGAXphFa. Install the free TestFlight app from the Mac App Store, open the link and click Install. The OAuth project is in production, so any Google account can sign in; until this verification is approved, Google shows the unverified app warning (click Advanced, then "Go to Gestor de Correos"). Steps: open Gestor de Correos, click "Buscar en Gmail" (Search Gmail), sign in with any Google account and grant access; then search by sender, select messages and use the label, archive and Trash buttons.

5. Privacy policy. https://gcorreos.efjdev.com/privacy.html (updated November 18, 2026) states what data is accessed (raw message data and locally computed aggregate counts), how it is used, that it is shared with no one, how it is protected (TLS, OAuth, macOS App Sandbox, user-only file permissions, loopback-only interface) and how it is retained and deleted.

6. Limited Use and AI. The data is used only to provide the user-facing features. It is never sold, transferred, used for advertising or used to train AI models. The optional AI feature only accepts a local model running on the user's own Mac; remote AI providers are refused by the app. The privacy policy contains the Limited Use statement: "The app's use and transfer of information received from Google APIs adheres to the Google API Services User Data Policy, including the Limited Use requirements."

7. Use case. The app organizes the user's own mailbox. It does not send email, so cold email and email warming do not apply. It does not use Data Portability APIs.

8. Security assessment. The app has no backend: restricted scope data is not stored on, transmitted to or accessed from or through any server of ours or of a third party. Following the restricted scope verification guide, we understand the CASA assessment does not apply. Please confirm, or tell us what you need to assess it.

Source code: https://github.com/edfrutos/gestor-correos-gmail

Best regards,
EDF Developer
```

## Comprobaciones en la v1.4.1 de TestFlight

Con la build 8 instalada desde TestFlight, antes de grabar el vídeo. Pasadas el 2026-11-15: las cuatro que dependían de la build 8, con ella; las demás, en la build 7:

- [x] La ventana «Ocultos locales» no muestra la sección «Eliminación permanente» y
  su texto inicial no habla de borrar en Gmail.
- [x] «Mover a la Papelera» pide confirmación, el mensaje aparece en la Papelera de
  Gmail y desaparece de «Ocultos locales». Desde Gmail se puede recuperar.
- [x] 🛠 Configuración no ofrece importar `credentials.json` y, en la IA, propone
  `llama3` y `ollama`, sin mencionar `gpt-4o-mini`, `sk-…` ni `.env`.
- [x] 🛠 Configuración rechaza `https://api.openai.com/v1` con «IA remota no
  disponible», y también `http://localhost:11434/v1` con un modelo `…:cloud`.
- [x] Un modelo local en `http://localhost:11434/v1` sigue funcionando, si tienes
  Ollama.
- [x] Con Ollama y `llama3`, «Sugerir reglas ahora» propone reglas (en la build 7
  fallaba con «Expecting value»).
- [x] En «Ocultos locales», tras desplazar el contenido, la ✕ sigue visible y cierra;
  Escape también cierra el modal.
- [x] La cuenta de demostración busca, etiqueta, archiva y exporta sin errores.
- [x] Con la app abierta, revocar el acceso en `myaccount.google.com/permissions`:
  la siguiente búsqueda avisa de que la autorización expiró o fue revocada, y la
  posterior abre Google sin reiniciar la app.
- [x] Abrir en el visor un `.eml` con imágenes remotas: el texto se lee, las imágenes
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
   nombre de la app y el permiso solicitado. Google describe `gmail.modify` con un
   texto fijo que menciona redactar y enviar: aclararlo en voz o subtítulo
   (*Google's standard description for this scope mentions sending, but the app
   never drafts or sends email*). Conceder el acceso.
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

**2026-11-25 — Sin evaluación CASA: cliente compartido sin verificar + cliente propio.**
Google aceptó el vídeo y el alcance (`gmail.modify`), pero exige la evaluación de
seguridad ADA-CASA AL1 antes del 22-02-2027, con renovación anual y de pago. El
usuario decide no hacerla. Consecuencias y plan:

- El proyecto sigue «En producción» sin verificar: quien use el cliente incluido
  ve el aviso «Google no ha verificado esta aplicación» y el proyecto admite como
  máximo **100 cuentas en total**, para siempre (no se reinicia).
- A partir de la v1.4.3, la descarga directa ofrece en 🛠 Configuración usar un
  **cliente propio** y volver al incluido. La guía es
  [`CLIENTE_PROPIO.md`](CLIENTE_PROPIO.md): proyecto en **modo personal** de
  Google Cloud, que no necesita verificación, no tiene límite de usuarios ni
  caducidad de 7 días y no muestra el aviso, pero solo admite la cuenta que lo crea.
- Si no se completa la CASA en el plazo, la solicitud de verificación quedará sin
  aprobar; no hace falta responder al hilo.
- La Mac App Store sigue en pausa: sin verificación, una app de la tienda con este
  cliente quedaría igualmente limitada a 100 cuentas.

