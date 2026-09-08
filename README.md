# Gestor de Correos — Servidor Local

Panel local de inteligencia operativa para consultar, organizar y tratar correos técnicos de Gmail. Detecta riesgos (SSL, facturas, seguridad) y automatiza el orden del buzón real sin exponer datos fuera del equipo local o VPN privada.

**Estado actual:** Milestones v1–v7.5 completados · v8 (refinamiento UX y mantenimiento) sustancialmente completo · **136 pruebas verdes** · Plan de testeo humano 30/30 ✅
Estado detallado y canónico: [`.planning/STATE.md`](.planning/STATE.md).

## Créditos

- **Creador:** EDF Developer
- **Usuario:** edefrutos

---

## Características Principales

| Área | Funcionalidad |
|------|--------------|
| **Inteligencia** | Clasificación semántica por categorías y severidad sin persistir contenidos en disco |
| **Búsqueda** | Remitente, texto literal nativo Gmail y rangos de fechas (`after`/`before`) |
| **Gestión Gmail** | Archivar (quitar de Inbox) y etiquetar individualmente o por lotes |
| **Automatización** | Reglas personalizadas con auto-etiquetado y auto-archivado sincronizado con Gmail |
| **Etiquetas** | Selector cargado al arrancar · botón "+" para crear etiquetas sin salir del formulario |
| **IA Opcional** | Sugerencias de reglas basadas en acciones y resúmenes operativos de incidentes |
| **Exportación** | Guardado persistente en `/exports` (`.eml` individual o `.zip` por lotes) |
| **Lector EML** | Visor nativo de `.eml` con renderizado HTML seguro y **descarga de adjuntos** |
| **macOS** | Abre cualquier `.eml` desde el Finder con "Acciones rápidas" |
| **Despliegue remoto** | VPN (Tailscale/WireGuard), modo headless, configuración completa por `.env` |
| **Borrado permanente** | Aislado bajo autorización explícita y confirmación reforzada |

---

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
```bash
cp .env.example .env
```

Variables disponibles:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HOST` | `localhost` | Interfaz de red. Usa `0.0.0.0` para VPN/remoto. |
| `PORT` | `8765` | Puerto de escucha. |
| `HEADLESS` | `0` | `1` = no abre navegador (ideal para SSH/servidor). |
| `ALLOWED_ORIGINS` | — | URLs adicionales permitidas, separadas por coma. La barra final es opcional. |
| `ENABLE_PERMANENT_DELETE` | `0` | `1` = habilita la frontera de borrado irreversible. |
| `AI_BASE_URL` | — | URL base del proveedor IA (sin `/chat/completions`). |
| `AI_API_KEY` | — | Clave API del proveedor (permanece solo en el backend). |
| `AI_MODEL` | — | Nombre del modelo (ej. `gpt-4o-mini`). |

> **Importante:** la variable es `AI_BASE_URL`, no `AI_API_URL`.

---

## Uso

### Iniciar el servidor
```bash
.venv/bin/python server.py
```
La primera búsqueda abre el flujo OAuth de Google. El token se guarda en `token.json` con scope `gmail.modify`.

### Abrir un archivo .eml directamente
```bash
.venv/bin/python server.py --open "/ruta/al/archivo.eml"
```
Si el servidor ya está en marcha, abre el visor en la instancia activa.

### Flujo habitual
1. **Buscar** — remitente, texto libre o rango de fechas.
2. **Revisar** — clasificación automática por categoría y severidad.
3. **Actuar** — archivar, etiquetar, ocultar, exportar o aplicar reglas.
4. **Automatizar** — crear reglas con auto-etiquetado o auto-archivado.

### Crear una regla de automatización
1. Panel superior → sección **Reglas personalizadas**.
2. Rellena Nombre, Proveedor (dominio) y/o Palabras clave.
3. En **Vincular etiqueta de Gmail**: selecciona una etiqueta existente o pulsa **+ Nueva** para crearla sin salir del formulario.
4. Marca **Aplicar etiqueta automáticamente** y/o **Archivar automáticamente**.
5. Pulsa **+ Añadir regla**. La próxima búsqueda del remitente aplicará las acciones.

### Borrado Permanente
1. Asegúrate de tener `ENABLE_PERMANENT_DELETE=1` en `.env`.
2. Reinicia el servidor.
3. En la bandeja de ocultos: **Autorizar borrado permanente** → genera `delete_token.json`.
4. Selecciona mensajes → **Eliminar permanentemente** → escribe la confirmación exacta.

---

## API Local

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/status` | Estado de tokens, Gmail y capacidad destructiva |
| GET | `/api/config` | Categorías, colores y reglas base |
| GET | `/api/search` | Búsqueda: `sender`, `q`, `after`, `before`, `max` |
| GET | `/api/labels` | Lista de etiquetas de usuario en Gmail |
| POST | `/api/labels` | Crea una nueva etiqueta en Gmail |
| GET | `/api/state` | Estado local persistido (fuentes, reglas, ocultos) |
| POST | `/api/state` | Guarda el estado local |
| GET | `/api/message` | Metadatos y adjuntos de un mensaje |
| GET | `/api/attachment` | Descarga un adjunto de Gmail |
| GET | `/api/hidden` | Lista paginada de mensajes ocultos |
| POST | `/api/messages/archive` | Archiva correos por lotes (retira INBOX) |
| POST | `/api/messages/label` | Aplica etiqueta (y opcionalmente archiva) por lotes |
| POST | `/api/messages/export` | Exporta `.eml` o `.zip` al directorio `/exports` |
| GET | `/api/exports` | Lista los archivos en `/exports` |
| GET | `/api/read-eml` | Parsea un `.eml` del directorio `/exports` |
| POST | `/api/read-eml` | Parsea un `.eml` enviado como bytes (adjuntos incluidos en base64) |
| POST | `/api/ai-suggest-rules` | Sugiere reglas basadas en actividad reciente |
| POST | `/api/ai-summary` | Resumen IA del informe operativo |
| POST | `/api/delete-permanent` | Borrado físico irreversible (máx. 100/lote) |
| POST | `/api/authorize-delete` | Inicia el flujo OAuth destructivo |
| POST | `/api/revoke-delete` | Revoca el token destructivo |

---

## Seguridad y Privacidad

- **Zero-Persistence**: los cuerpos de los correos nunca se escriben en disco.
- **Archivos sensibles**: `credentials.json`, `token.json`, `delete_token.json` y `app_state.json` con permisos `600`. Están en `.gitignore`.
- **CORS & Host**: el servidor rechaza orígenes externos y cabeceras Host no autorizadas. `ALLOWED_ORIGINS` acepta URLs con o sin barra final.
- **Secretos IA**: la clave API permanece únicamente en el backend; el frontend nunca la recibe.
- **Frontera destructiva**: el scope `https://mail.google.com/` está aislado en `delete_token.json`, independiente del token de lectura normal.

---

## Tests

```bash
.venv/bin/python -m pytest
```

Suite automatizada: **136 pruebas, todas verdes** (Fases 31, 32, 33; 2026-09-08). Historial
y decisiones de diseño en [`.planning/STATE.md`](.planning/STATE.md) y
[`.planning/DECISIONS.md`](.planning/DECISIONS.md).
