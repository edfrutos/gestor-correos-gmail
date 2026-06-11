# Phase 1 Summary: Seguridad y Base Operativa

## Outcome

Se endurecio la app local manteniendo el flujo actual: `.venv/bin/python server.py` sirve `index.html` y la UI usa la API local para buscar en Gmail en modo readonly.

## Cambios realizados

- `server.py` usa `ThreadingHTTPServer` para evitar bloqueo por una unica peticion larga.
- Se elimino el CORS abierto de las respuestas JSON. La UI debe servirse desde `http://localhost:8765`.
- `/api/status` ahora es pasivo: informa dependencias, `credentials.json` y `token.json` sin llamar a Gmail ni abrir OAuth.
- La autenticacion OAuth queda diferida hasta una busqueda explicita en `/api/search`.
- `/api/search` valida `sender` como dominio/email simple y `max` como entero entre 1 y 100.
- Los errores de API devuelven JSON consistente con `status`, `error` y `detail`.
- Los errores reales de Gmail se exponen como JSON en vez de devolverse como listas vacias.
- `index.html` usa endpoints relativos mediante `const API = ''`.
- El escape HTML del frontend cubre `&`, `<`, `>`, comillas dobles y comillas simples.
- Los enlaces detectados en cuerpos de correo se validan con `URL` antes de insertarse como anchors.
- Mensajes dinamicos de estado y error usan `textContent` cuando no necesitan marcado.
- Los enlaces a Gmail limpian el `id` antes de construir la URL.
- `README.md` y `AGENTS.md` documentan instalacion desde `requirements.txt`, estado pasivo y ausencia de CORS abierto.
- La instalacion se ajusto a `.venv` para evitar el bloqueo PEP 668 del Python de Homebrew en macOS.
- La UI ya no incorpora remitentes si la busqueda Gmail falla o si no devuelve correos nuevos.
- La busqueda de remitentes se corrigio para actuar como localizacion: si Gmail devuelve correos, se filtra la vista por ese remitente y quedan disponibles seleccion, exportacion y ocultado aunque no haya mensajes nuevos respecto a los ya cargados.

## Decisiones

- Mantener una sola aplicacion sin build tooling ni separacion de frontend/backend para no ampliar el alcance de la fase.
- No permitir CORS abierto porque la UI se sirve desde el mismo origen local.
- Hacer `/api/status` pasivo aunque eso impida saber si el token es realmente valido sin una busqueda.
- Permitir que la primera busqueda dispare OAuth si hay `credentials.json` pero falta `token.json`.

## Verificacion

- `.venv/bin/python -m py_compile server.py`: OK.
- Checks directos de `parse_max` y `validate_sender`: OK.
- `GET /api/status`: OK, responde JSON sin OAuth.
- `GET /api/search?sender=&max=abc`: OK, error JSON controlado.
- `GET /api/search?sender=plesk.com&max=abc`: OK, error JSON controlado.
- `GET /api/search?sender=bad%20sender&max=30`: OK, error JSON controlado.
- `GET /`: OK, sirve `index.html`.

## Limitaciones

- Correccion posterior: se creo `.venv`, se instalaron dependencias y `/api/status` ya devuelve `gmail_lib: true`, `credentials: true`, `token: true`.
- Correccion posterior: se activo Gmail API en Google Cloud y la busqueda real de remitentes quedo funcionando.

## Archivos modificados

- `server.py`
- `index.html`
- `README.md`
- `AGENTS.md`
- `.gitignore`
