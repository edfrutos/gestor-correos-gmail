# Phase 2 Summary: Modularización y Tests

## Outcome

La lógica crítica dejo de vivir en un unico `server.py` y paso a modulos testeables. El flujo operativo se mantiene con `.venv/bin/python server.py`.

## Cambios realizados

- `server.py` queda como capa HTTP fina: sirve `index.html`, enruta `/api/status` y `/api/search`, y emite JSON.
- `gmail_client.py` concentra OAuth, estado Gmail, normalizacion de fechas, tags, mensajes y busqueda.
- `validators.py` concentra `ApiError`, `parse_max(raw)` y `validate_sender(raw)`.
- `classifier.py` concentra reglas de categorias y `classify_email(email)`.
- `requirements.txt` incluye `pytest`.
- Se creo suite `tests/` con cobertura para validacion, fechas, tags, normalizacion de mensajes, clasificacion y respuestas API.

## Decisiones

- Mantener el frontend sin cambios funcionales en esta fase.
- No hacer tests que llamen a Gmail real ni abran OAuth.
- Usar monkeypatch en tests de API para simular Gmail y errores.
- Mantener los mensajes JSON en español para no romper la UI.

## Verificacion

- `.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py`: OK.
- `.venv/bin/python -m pytest`: OK, 31 tests pasan.
- `GET /api/status`: OK, devuelve `gmail_lib: true`, `credentials: true`, `token: true`.
- `GET /`: OK, sirve `index.html`.
- `GET /api/search?sender=&max=abc`: OK, error JSON controlado.

## Archivos modificados

- `server.py`
- `requirements.txt`
- `README.md`
- `AGENTS.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`

## Archivos añadidos

- `gmail_client.py`
- `validators.py`
- `classifier.py`
- `tests/test_validators.py`
- `tests/test_gmail_client.py`
- `tests/test_classifier.py`
- `tests/test_server_api.py`
- `.planning/phases/02-modularizacion-tests/02-PLAN.md`
- `.planning/phases/02-modularizacion-tests/02-SUMMARY.md`
- `.planning/phases/02-modularizacion-tests/02-VERIFICATION.md`
