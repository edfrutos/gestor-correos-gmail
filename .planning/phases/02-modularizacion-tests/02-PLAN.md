# Phase 2 Plan: Modularización y Tests

## Objective

Separar la lógica crítica de `server.py` en módulos testeables y añadir una suite `pytest` enfocada en validación, fechas, clasificación y respuestas API, manteniendo el flujo operativo actual con `.venv/bin/python server.py`.

## Scope

- Extraer acceso Gmail y normalización de mensajes a `gmail_client.py`.
- Extraer validación de parámetros y helpers de API a `validators.py`.
- Extraer reglas de clasificación compartibles a `classifier.py`.
- Mantener `server.py` como capa HTTP fina basada en `ThreadingHTTPServer`.
- Añadir `pytest` a `requirements.txt`.
- Crear tests unitarios para validación, fechas, clasificación y errores API.

## Implementation Tasks

### Backend Modules

- Crear `validators.py` con `ApiError`, `parse_max(raw)` y `validate_sender(raw)`.
- Crear `gmail_client.py` con constantes OAuth, `gmail_status()`, `gmail_error_detail()`, `norm_date()`, `tag()` y `search(sender, max_r)`.
- Crear `classifier.py` con reglas de categorías y función `classify_email(email)`.
- Actualizar `server.py` para importar esos módulos y quedarse con routing HTTP, JSON y archivos estáticos.

### Tests

- Añadir `pytest` a `requirements.txt`.
- Crear `tests/test_validators.py`.
- Crear `tests/test_gmail_client.py` para fechas, tags y errores no-HTTP.
- Crear `tests/test_classifier.py`.
- Crear `tests/test_server_api.py` para helpers JSON/errores sin llamar a Gmail real, usando monkeypatch cuando haga falta.

## Acceptance Criteria

- `.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py` pasa.
- `.venv/bin/python -m pytest` pasa.
- `server.py` no contiene lógica OAuth directa ni regex de validación de `sender`.
- `/api/status` sigue siendo pasivo.
- `/api/search` mantiene errores JSON con `status`, `error` y `detail`.
- La UI sigue sirviéndose desde `http://localhost:8765`.

## Risks

- Mover Gmail/OAuth puede romper el token existente si cambian rutas de `credentials.json` o `token.json`.
- Duplicar reglas de clasificación entre Python y JavaScript puede generar divergencia si no se documenta bien.
- Los tests de API no deben abrir OAuth ni llamar a Gmail real.

## Verification Commands

```bash
.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py
.venv/bin/python -m pytest
.venv/bin/python server.py
```

Manual:

- Abrir `http://localhost:8765`.
- Comprobar `/api/status`.
- Buscar un remitente real.
- Probar un remitente inválido.
- Confirmar selección/exportación/ocultado desde la UI.

## Out of Scope

- Persistencia local.
- Reglas editables desde UI.
- Escritura en Gmail.
- Reescritura visual del frontend.
