# Phase 4 Summary: Inteligencia Operativa

## Outcome

La app dejó de comportarse como un listado de correo y pasó a presentar una cola operativa priorizada con severidad visible, agrupación principal por proveedor/remitente y exportación Markdown/JSON con elección explícita de alcance.

## Changes made

- Añadida severidad fija por categoría en `classifier.py`.
- Enriquecida la normalización Gmail en `gmail_client.py` con `categories`, `severity` y `severity_reason`.
- Rehecha la vista principal de `index.html` para mostrar una cola operativa agrupada por proveedor con severidad visible y motivo antes del extracto.
- Reemplazado el flujo de exportación por un modal que obliga a elegir alcance: vista filtrada o conjunto completo.
- Limitado el export de Fase 4 a Markdown y JSON.
- Añadidos tests para clasificación, mensajes Gmail y passthrough de API.

## Verification

- `.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py`: OK
- `node --check` del JavaScript embebido: OK
- `.venv/bin/python -m pytest`: OK, 61 tests pasan
- `GET /api/status`: OK
- `GET /`: OK

## Files modified

- `classifier.py`
- `gmail_client.py`
- `index.html`
- `tests/test_classifier.py`
- `tests/test_gmail_client.py`
- `tests/test_server_api.py`
- `.planning/STATE.md`

## Residual risks

- La UI sigue en un único `index.html`; si la cola operativa crece, convendrá separar render y utilidades.
- La copia de severidad se refleja también en la UI para el stock local pre-cargado, pero la fuente de verdad de Gmail queda centralizada en Python.
- La exportación sigue siendo client-side; eso es suficiente para esta fase, pero cualquier exportación con más lógica de negocio podría beneficiarse de un endpoint dedicado.
