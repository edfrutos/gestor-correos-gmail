# Usar tu propio cliente de Google

Gestor de Correos se conecta a Gmail con un **cliente de Google** (un «ID de
cliente OAuth»). La app trae uno incluido, compartido por todas las personas
que la usan. Google todavía no lo ha verificado, y eso tiene dos efectos:

- Al iniciar sesión aparece el aviso **«Google no ha verificado esta
  aplicación»**. Pulsa **Configuración avanzada** y después **Ir a Gestor de
  Correos**.
- Ese cliente admite **como máximo 100 cuentas en total**, para siempre. Cuando
  se llene, Google dejará de aceptar cuentas nuevas con él.

Si no puedes usar el cliente incluido, o prefieres no depender de él, crea el
tuyo. Es gratis, tarda unos 10 minutos y solo hay que hacerlo una vez. Con tu
propio cliente **no hay aviso, ni límite de cuentas, ni caducidad semanal**, y tus
correos siguen sin salir de tu Mac.

## Lo que necesitas

- La cuenta de Gmail que vas a usar en Gestor de Correos. El cliente que crees
  **solo funcionará con esa cuenta**.
- Gestor de Correos 1.4.3 o posterior.

## 1. Crea el proyecto y el cliente en modo personal

1. Entra en Google Cloud con tu cuenta de Gmail y abre la página de alta en
   modo personal: <https://console.cloud.google.com/auth/overview/personal>.
   La primera vez, Google te pedirá aceptar sus condiciones de servicio.
2. Sigue el asistente. Crea un proyecto nuevo (por ejemplo, «Gestor de
   Correos personal») configurado en **modo personal** y su cliente OAuth.
   - Si te pide el tipo de aplicación, elige **App de escritorio**
     («Desktop app»).
   - Como nombre de la app puedes poner «Gestor de Correos».
3. Al terminar, **descarga el JSON del cliente** (botón de descarga junto al
   cliente creado). Es un archivo con un nombre parecido a
   `client_secret_….json`. Guárdalo en un lugar privado: no lo compartas.

> El modo personal se elige una sola vez y no se puede cambiar después. Es lo
> que quieres: el proyecto queda solo para tu cuenta y Google no exige
> verificarlo.

## 2. Activa la Gmail API en ese proyecto

1. Con el proyecto nuevo seleccionado arriba, abre
   <https://console.cloud.google.com/apis/library/gmail.googleapis.com>.
2. Pulsa **Habilitar**.

## 3. Impórtalo en Gestor de Correos

1. Abre Gestor de Correos y entra en **🛠 Configuración → Cuenta de Google**.
2. Pulsa **Usar mi propio cliente (credentials.json)…** y elige el JSON que
   descargaste.
3. Haz una búsqueda. Se abrirá el navegador para iniciar sesión: entra con **la
   misma cuenta** con la que creaste el proyecto y acepta el permiso de Gmail.

Listo. La app recordará tu cliente aunque se actualice.

## Si algo falla

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `client_user_mismatch` | Has iniciado sesión con una cuenta distinta de la que creó el proyecto. | Inicia sesión con la cuenta propietaria del proyecto, o crea otro proyecto con la cuenta que quieres usar. |
| «Gmail API has not been used in project…» | Falta el paso 2. | Habilita la Gmail API en el proyecto y repite la búsqueda. |
| «No es un cliente OAuth de tipo App de escritorio» | El JSON es de otro tipo de cliente (por ejemplo, «Aplicación web»). | Crea un cliente de tipo **App de escritorio** en ese mismo proyecto y descarga su JSON. |
| Tu cuenta es de una organización (Google Workspace) | El administrador puede tener bloqueado el acceso a Gmail para apps propias. | Pide al administrador que lo permita. |

## Volver al cliente incluido

En **🛠 Configuración → Cuenta de Google**, pulsa **Volver al cliente
incluido**. La próxima búsqueda pedirá iniciar sesión otra vez.

## Retirar el acceso

En cualquier momento puedes retirar el permiso desde
<https://myaccount.google.com/connections>. Si ya no vas a usar tu proyecto,
puedes borrarlo en Google Cloud; no tiene coste.
