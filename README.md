# Gestor de Correos — Servidor Local

Panel local de inteligencia operativa para consultar, organizar y tratar correos técnicos de Gmail. La herramienta permite detectar riesgos (SSL, facturas, seguridad) y automatizar el orden del buzón real sin exponer datos fuera del equipo local o VPN privada.

**Estado actual:** Milestone v7.0 completado. La suite automatizada contiene **129 pruebas** superadas.

## Créditos

- **Creador:** EDF Developer
- **Usuario:** edefrutos

## Características Principales

- **Inteligencia Local**: Clasificación semántica por categorías y severidad sin persistir contenidos en disco.
- **Búsqueda Avanzada**: Filtros por remitente, texto literal nativo de Gmail y rangos de fechas (`after`/`before`).
- **Gestión Gmail**: Archivar (quitar de Inbox) y etiquetar correos individualmente o por lotes.
- **Automatización**: Reglas personalizadas con auto-etiquetado y auto-archivado sincronizado con Gmail.
- **IA Opcional**: Sugerencias de reglas basadas en tus acciones y resúmenes operativos de incidentes.
- **Exportación Íntegra**: Guardado persistente en el directorio `/exports` (sin descargas de navegador).
- **Lector Integrado**: Visor nativo de archivos `.eml` con renderizado HTML seguro (iframe).
- **Integración con macOS**: Abre cualquier archivo `.eml` desde el Finder usando el menú "Acciones rápidas".
- **Despliegue Remoto Seguro**: Soporte para VPN (Tailscale/Wireguard), modo headless y configuración por `.env`.
- **Frontera Destructiva**: Borrado permanente aislado bajo autorización explícita y confirmación reforzada.

## Instalación y Configuración

### 1. Entorno (una sola vez)
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 2. Google Cloud (una sola vez)
1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com).
2. Activa la **Gmail API**.
3. Credenciales → Crear → **ID de cliente OAuth 2.0** → Aplicación de escritorio.
4. Descarga el JSON y guárdalo como `credentials.json` en la raíz del proyecto.

### 3. Configuración (.env)
Copia el ejemplo y ajusta tus variables:
```bash
cp .env.example .env
```
- `HOST`: Interfaz de red (ej. tu IP de VPN).
- `PORT`: Puerto de escucha (default 8765).
- `HEADLESS`: `1` para no abrir navegador (ideal para servidores SSH).
- `AI_BASE_URL` / `AI_MODEL`: Para habilitar funciones de IA.

## Uso

### Iniciar servidor
```bash
.venv/bin/python server.py
```
- La primera acción de búsqueda abrirá el flujo de autorización OAuth.
- La aplicación guardará `token.json` con permisos de lectura y modificación (`gmail.modify`).

### Gestión de correos
- **Localizar**: Usa el panel superior para buscar remitentes o rangos de fechas.
- **Ocultar**: Acción puramente local para limpiar tu panel de control.
- **Archivar**: Acción real en Gmail que retira el correo de Recibidos y lo oculta localmente.
- **Etiquetar**: Aplica etiquetas de Gmail (o crea nuevas sobre la marcha) a la selección.

### Borrado Permanente
Para habilitar la capacidad de borrado irreversible en Gmail:
1. Asegúrate de tener `ENABLE_PERMANENT_DELETE=1` en tu `.env`.
2. Pulsa **Autorizar borrado permanente** en la bandeja de ocultos. Esto genera `delete_token.json` con el scope restringido total.

## API local

- `GET /api/status`: Estado de dependencias y tokens.
- `GET /api/config`: Diccionario unificado de categorías, colores y reglas base.
- `GET /api/search`: Búsqueda avanzada con `sender`, `q`, `after`, `before` y `max`.
- `GET /api/labels`: Lista de etiquetas de usuario en Gmail.
- `POST /api/labels`: Crea una nueva etiqueta en Gmail.
- `POST /api/messages/archive`: Archiva correos por lotes (retira INBOX).
- `POST /api/messages/label`: Aplica una etiqueta (y opcionalmente archiva) por lotes.
- `POST /api/messages/export`: Descarga `.eml` o `.zip` con el contenido RFC822 crudo.
- `POST /api/ai-suggest-rules`: Sugiere reglas de automatización basadas en actividad.
- `POST /api/delete-permanent`: Borrado físico irreversible en Gmail (máx. 100/lote).

## Seguridad y Privacidad

- **Zero-Persistence**: Los cuerpos de los correos nunca se escriben en disco.
- **Archivos Sensibles**: `credentials.json`, `token.json` y `app_state.json` se guardan con permisos `600`.
- **CORS & Host**: El servidor rechaza orígenes externos y cabeceras Host no autorizadas.
- **Secretos**: Las claves de API IA permanecen únicamente en el backend.

## Tests
```bash
.venv/bin/python -m pytest
```
