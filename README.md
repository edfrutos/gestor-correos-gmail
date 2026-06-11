# Gestor de Correos — Servidor Local

Panel local para consultar y tratar correos técnicos de Gmail. Las operaciones normales permanecen readonly; el borrado permanente de ocultos usa una autorización destructiva separada, persistente entre sesiones, revocable y desactivada por defecto.

**Estado actual:** milestones v1 a v5 completados. La suite automatizada contiene 121 pruebas.

## Créditos

- **Creador:** EDF Developer
- **Usuario:** edefrutos

## Instalación (una sola vez)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Configurar Gmail API (una sola vez)

1. Ve a https://console.cloud.google.com
2. Crea un proyecto nuevo (o usa uno existente)
3. Activa la **Gmail API**
4. Credenciales → Crear → **OAuth 2.0** → Aplicación de escritorio
5. Descarga el JSON y renómbralo `credentials.json`
6. Cópialo a esta carpeta (junto a `server.py`)

## Iniciar

```bash
.venv/bin/python server.py
```

- Se abre el navegador automáticamente en http://localhost:8765
- `/api/status` comprueba el estado de forma pasiva, sin abrir OAuth
- La primera búsqueda en Gmail abrirá una ventana de autorización de Google si todavía no existe `token.json`
- Si `token.json` ha expirado o fue revocado, la siguiente búsqueda lo sustituye y abre una autorización nueva.
- Una vez autorizado, el token se guarda en `token.json` para futuras sesiones

## Uso

- Los correos de Vultr, Plesk y el servidor están pre-cargados
- Para añadir un remitente nuevo (ej: `web.dev`, `paypal.com`, `factura@cualquier.com`):
  - Escríbelo en el input y pulsa **"+ Buscar en Gmail"**
  - El servidor busca en tiempo real en tu Gmail
  - Los correos encontrados se integran en la lista con todas las funcionalidades
- Exportar, filtrar, categorizar y ocultar localmente funciona igual para todos los correos
- Las reglas personalizadas permiten combinar proveedor y palabras clave para asignar categoría y severidad
- **Resumen periódico** genera vistas de los últimos 7 o 30 días con severidades, proveedores, categorías y acciones prioritarias; puede copiarse o descargarse en Markdown
- Cada resumen compara el período con la ventana anterior equivalente y destaca aumentos por proveedor/categoría y asuntos recurrentes
- Las fuentes añadidas, reglas personalizadas, correos ocultos y preferencias básicas se guardan en `app_state.json`
- **Ocultar** sólo oculta el correo en la vista local; no borra, archiva ni etiqueta nada en Gmail
- Si hay correos ocultos, aparece **Gestionar ocultos** para restaurarlos, conservarlos, limpiar huérfanos o borrarlos permanentemente
- La bandeja de ocultos usa páginas de 20 y permite seleccionar rangos con `Shift` o alternar mensajes con `Cmd/Ctrl`
- La UI separa las acciones que sólo afectan al estado local de las acciones irreversibles que afectan a Gmail
- Un ID que Gmail ya no puede localizar se clasifica como huérfano y se purga de la referencia oculta y de la sesión cargada
- El borrado permanente sólo acepta mensajes ocultos, exige confirmación escrita exacta y acepta como máximo 100 IDs por solicitud
- El backend procesa internamente esos lotes en tandas de 20 y devuelve un resultado individual por ID

Para habilitar localmente la autorización destructiva:

```bash
ENABLE_PERMANENT_DELETE=1 .venv/bin/python server.py
```

Después pulsa **Autorizar borrado permanente** en la bandeja de ocultos. Esto genera `delete_token.json` con el scope restringido `https://mail.google.com/`. El token válido o renovable se reutiliza entre sesiones. Puedes cerrar ese acceso con **Revocar autorización**, que elimina el token y crea el marcador local `delete_token.revoked`. El borrado es inmediato e irreversible.

## API local

- `GET /api/status`: devuelve estado local de dependencias, `credentials.json` y `token.json` sin conectar con Gmail.
- `GET /api/search?sender=plesk.com&max=30`: busca por dominio o email. `sender` debe ser un dominio/email simple y `max` limita el total de mensajes devueltos entre 1 y 100.
- `GET /api/state`: devuelve el estado local guardado.
- `POST /api/state`: guarda fuentes añadidas, reglas personalizadas, IDs ocultos y preferencias de filtros.
- `GET /api/attachment?message_id=...&attachment_id=...`: abre un adjunto concreto usando Gmail readonly.
- `GET /api/message?message_id=...`: carga un mensaje concreto y sus adjuntos usando Gmail readonly.
- `GET /api/hidden?page=1`: resuelve bajo demanda una página de IDs ocultos persistidos.
- `POST /api/ai-summary`: resume explícitamente contenido enviado por la UI usando el proveedor AI configurado; permanece desactivado si faltan `AI_BASE_URL` o `AI_MODEL`.
- `POST /api/delete-authorize`: inicia explícitamente la autorización destructiva si está habilitada por entorno.
- `POST /api/delete-revoke`: revoca la autorización destructiva separada sin afectar a Gmail readonly.
- `POST /api/delete-permanent`: borra permanentemente hasta 100 IDs ocultos con confirmación textual exacta.

Los errores de API se devuelven como JSON con `status`, `error` y `detail`.

## Estado local

El archivo `app_state.json` se genera automáticamente junto a `server.py`. Guarda sólo:

- Fuentes/remitentes añadidos por el usuario
- Reglas personalizadas con proveedor, palabras clave, operador alguna/todas, categoría y severidad
- IDs de correos ocultos localmente
- Auditoría mínima de borrado permanente: ID, resultado y fecha
- Preferencias básicas de filtro y búsqueda

No guarda cuerpos, snippets, asuntos, adjuntos ni contenido de Gmail. Para reiniciar la configuración local, detén el servidor y elimina `app_state.json`; se recreará con valores por defecto.

La app no incrusta asuntos, cuerpos ni correos de demostración en el frontend. Al arrancar consulta en Gmail las fuentes fijas y las añadidas por el usuario; por eso un huérfano purgado no puede reconstruirse al recargar.

Los resúmenes periódicos se calculan en el navegador sobre los correos cargados y visibles. Tampoco se guardan en `app_state.json`.

Las tendencias son señales operativas deterministas sobre los correos cargados; no estiman importes ni consultan servicios externos.

## Resumen AI opcional

La integración AI está desactivada por defecto. Para usar un endpoint compatible con OpenAI:

```bash
AI_BASE_URL=http://localhost:11434/v1 AI_MODEL=modelo-local .venv/bin/python server.py
```

Para un proveedor remoto, añade `AI_API_KEY`. El navegador sólo envía el resumen operativo cuando pulsas **Resumir con AI** y pide confirmación antes de transmitirlo a un endpoint remoto. La clave permanece únicamente en el proceso Python.

## Tests

```bash
.venv/bin/python -m pytest
```

## Archivos

```
gestor_correos/
├── server.py          # Servidor local (este archivo)
├── gmail_client.py    # Cliente Gmail, OAuth y normalización de mensajes
├── validators.py      # Validación de parámetros de API
├── classifier.py      # Reglas de clasificación testeables
├── storage.py         # Persistencia local en app_state.json
├── ai_client.py       # Integración opcional con proveedor AI compatible
├── destructive_gmail.py # Autorización separada y borrado permanente
├── index.html         # Estructura de la interfaz web
├── static/app.css     # Estilos de la interfaz
├── static/app.js      # Estado, Gmail, filtros y render principal
├── static/summary.js  # Resúmenes, tendencias e integración AI
├── static/logo.svg    # Logo de la aplicación
├── static/favicon.svg # Favicon local
├── tests/             # Suite pytest
├── README.md          # Esta guía
├── CREDITS.md         # Créditos del proyecto
├── credentials.json   # Tu OAuth credentials (añadir manualmente)
├── token.json         # Token de sesión (se genera automáticamente)
├── delete_token.json  # Token destructivo separado, si se autoriza
├── delete_token.revoked # Marcador local de revocación destructiva
└── app_state.json     # Estado local generado automáticamente
```

## Seguridad local

- No subas `credentials.json` ni `token.json` a Git.
- No subas `delete_token.json`; tiene permiso restringido para borrar permanentemente correo.
- No subas `delete_token.revoked`; refleja el estado local de la autorización destructiva.
- Mantén `delete_token.json` con permisos privados; se genera con permisos `600`.
- El token destructivo se reutiliza entre sesiones mientras siga válido o renovable; usa **Revocar autorización** cuando quieras cerrar ese acceso.
- No habilites `ENABLE_PERMANENT_DELETE=1` salvo cuando necesites gestionar borrado permanente.
- No subas `app_state.json`; puede contener preferencias locales e IDs de mensajes.
- Mantén `credentials.json` con permisos privados (`chmod 600 credentials.json`); los archivos generados `token.json` y `app_state.json` se escriben con permisos `600`.
- La interfaz debe abrirse desde `http://localhost:8765`, no como archivo local.
- El servidor no expone CORS abierto; la UI y la API comparten el mismo origen local.
- El servidor rechaza cabeceras `Host` no locales y cabeceras `Origin` externas.
- Los adjuntos se leen bajo demanda desde Gmail y no se guardan en `app_state.json`.
