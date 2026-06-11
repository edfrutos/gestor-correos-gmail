# Phase 4 Verification: Inteligencia Operativa

## Automated checks

### Python compile

Command:

```bash
.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py
```

Result: PASS.

### Pytest

Command:

```bash
.venv/bin/python -m pytest
```

Result: PASS.

Observed:

```text
61 passed
```

### JavaScript syntax

Command:

```bash
node --check /private/tmp/gestor-correos-gmail-index.js
```

Result: PASS.

## HTTP smoke tests

Server command:

```bash
.venv/bin/python server.py
```

Result: PASS. Server responded on `http://127.0.0.1:8765`.

### `GET /api/status`

Result: PASS.

Observed JSON:

```json
{"status":"ok","ok":true,"can_search":true,"gmail_lib":true,"credentials":true,"token":true,"msg":"Token disponible"}
```

### `GET /`

Result: PASS. Server returned `index.html` with HTTP 200 and the updated Phase 4 copy:

- `⬇ Exportar informe`
- `Vista filtrada`
- `Conjunto completo`
- `Sin acciones pendientes`

## Manual coverage

The browser interaction path was checked by source and live HTML response:

- The default rendering path now groups by provider/remitente and surfaces severity.
- The export modal requires an explicit scope choice before copy/download.
- Export formats are Markdown and JSON only.
- Local hide remains `Ocultar` and does not mutate Gmail.

## Requirement coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PROD-01 | PASS | Queue rendering, severity badges/reasons, ordering, grouped operational sections |
| PROD-03 | PASS | Provider-first grouping with deterministic sorting |
| PROD-04 | PASS | Markdown/JSON export with explicit filtered/full scope choice |

## Status

Phase 4 execution passed.
