# Política de privacidad — Gestor de Correos

*Última actualización: 22 de octubre de 2026*

Gestor de Correos es una aplicación para macOS que organiza tu propio correo de
Gmail desde tu Mac. Esta política explica qué datos usa, dónde se guardan y con
quién se comparten. El desarrollador es EDF Developer (contacto:
[issues del proyecto](https://github.com/edfrutos/gestor-correos-gmail/issues)).

## Resumen

- **El desarrollador no recibe ningún dato tuyo.** La app no tiene servidores
  propios, ni analítica, ni publicidad, ni seguimiento.
- Tus correos se leen **directamente de Google a tu Mac** a través de la API de
  Gmail, con el permiso que tú concedes en la pantalla de autorización de Google.
- Todo lo que la app guarda se queda **en tu Mac**.
- Solo si tú configuras un proveedor de IA **remoto**, la app le envía el texto
  necesario para cada resumen o sugerencia que pidas, y antes te lo avisa.

## Datos de Google (Gmail) que usa la app

Con tu autorización, la app accede a tu cuenta de Gmail para:

- buscar y mostrar mensajes (remitente, asunto, fecha, etiquetas, fragmento y,
  cuando abres un mensaje, su contenido y adjuntos);
- aplicar las acciones que tú eliges: etiquetar, archivar, exportar a
  `.eml`/`.zip` y, solo si lo activas expresamente, borrar de forma permanente.

La app no usa tus datos de Gmail para ningún otro fin, no los vende, no los
transfiere a terceros (salvo el proveedor de IA que tú configures, ver abajo),
no los usa para publicidad y no los usa para entrenar modelos de IA.

El uso y la transferencia de la información recibida de las API de Google se
ajustan a la [Política de datos de usuario de los servicios de API de
Google](https://developers.google.com/terms/api-services-user-data-policy),
incluidos los requisitos de uso limitado (*Limited Use*).

## Qué se guarda en tu Mac

En la carpeta de datos de la app (en la versión de la Mac App Store, dentro de
su contenedor de App Sandbox):

- el token de autorización de Google (`token.json`, con permisos solo para tu
  usuario);
- tu configuración: fuentes, reglas, correos ocultos, ajustes de IA (la clave
  API, si la pones, se guarda ahí y nunca se muestra de nuevo);
- los correos que tú exportas, y una copia en la carpeta de respaldo si la
  eliges.

Puedes borrarlo todo desinstalando la app y su carpeta de datos, y revocar el
acceso a Gmail en cualquier momento en
[myaccount.google.com/permissions](https://myaccount.google.com/permissions).
El permiso adicional de borrado permanente se revoca también desde la propia
app («Revocar autorización»).

## Inteligencia artificial (opcional)

La IA está desactivada hasta que tú la configuras en 🛠 Configuración.

- Con un modelo **local** (p. ej. Ollama en tu Mac), nada sale de tu equipo.
- Con un proveedor **remoto** (p. ej. OpenAI, o un modelo «cloud» de Ollama),
  al pedir un resumen o sugerencias de reglas la app envía a ese proveedor los
  datos necesarios para ello (remitentes, asuntos y fragmentos de los correos
  cargados). La app te lo advierte y pide confirmación antes de enviarlo. Ese
  envío se rige por la política de privacidad del proveedor que elijas.

## Niños

La app no está dirigida a menores de 13 años ni recoge datos de ellos.

## Cambios

Si esta política cambia, la nueva versión se publicará en esta misma página con
su fecha.
