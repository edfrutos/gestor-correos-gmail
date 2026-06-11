# Phase 3 Summary: Persistencia Local

## Outcome

La herramienta ahora persiste estado local entre recargas del navegador y reinicios del servidor mediante `app_state.json`, sin cachear contenido de Gmail ni cambiar los permisos readonly.

## Cambios realizados

- Añadido `storage.py` con schema normalizado, validación y escritura atómica de `app_state.json`.
- Añadidos endpoints:
  - `GET /api/state`
  - `POST /api/state`
- Actualizado `index.html` para cargar estado antes del render inicial.
- Añadido guardado debounced de fuentes añadidas, correos ocultos y preferencias básicas.
- Añadida recuperación local de correos ocultos desde la UI.
- Actualizado `README.md` con documentación de estado local y `/api/state`.
- Añadido `app_state.json` a `.gitignore`.
- Añadidos tests de almacenamiento y endpoints de estado.
- Añadido indicador accesible de adjuntos en la cabecera del correo.
- Añadido endpoint readonly `/api/attachment` para abrir adjuntos bajo demanda sin guardarlos localmente.

## Decisiones cumplidas

- JSON local en vez de SQLite.
- Sin cache de cuerpos, snippets, asuntos, adjuntos ni metadatos completos de Gmail.
- "Borrar" sigue siendo ocultado local; no modifica Gmail.
- Restaurar ocultos es una acción local accesible mediante botón.

## Verificación

- `.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py storage.py`: OK.
- `.venv/bin/python -m pytest`: OK, 41 tests pasan.
- `node --check` del bloque JavaScript embebido en `index.html`: OK.
- `GET /api/status`: OK.
- `GET /api/state`: OK.
- `POST /api/state`: OK.
- `POST /api/state` con JSON inválido: error JSON 400 controlado.
- `GET /`: OK, sirve `index.html`.
- `app_state.json` inspeccionado tras pruebas: no contiene cuerpos, snippets, asuntos ni adjuntos.
- Los adjuntos se leen bajo demanda desde Gmail y no se persisten en `app_state.json`.

## Archivos modificados

- `server.py`
- `index.html`
- `README.md`
- `.gitignore`
- `tests/test_server_api.py`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`

## Archivos añadidos

- `storage.py`
- `tests/test_storage.py`
- `.planning/phases/03-persistencia-local/03-RESEARCH.md`
- `.planning/phases/03-persistencia-local/03-PATTERNS.md`
- `.planning/phases/03-persistencia-local/03-PLAN.md`
- `.planning/phases/03-persistencia-local/03-SUMMARY.md`
- `.planning/phases/03-persistencia-local/03-VERIFICATION.md`

## Riesgos residuales

- La restauración de correos ocultos para fuentes custom sólo muestra esos correos cuando la fuente vuelve a estar cargada desde Gmail, porque Phase 3 no cachea mensajes.
- La UI sigue siendo un único `index.html`; futuras fases deberían controlar el crecimiento del script.
- `app_state.json` queda generado localmente e ignorado por Git, pero puede contener IDs de mensajes y preferencias locales.
