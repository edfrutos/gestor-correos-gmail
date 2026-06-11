# Phase 2 Verification: Modularización y Tests

## Entorno

- Fecha: 2026-06-01
- Python: `.venv/bin/python`
- Servidor probado en `localhost:8765`

## Comandos ejecutados

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Resultado: OK. Se instalo `pytest`; las dependencias Gmail ya estaban presentes.

```bash
.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py
```

Resultado: OK.

```bash
.venv/bin/python -m pytest
```

Resultado:

```text
31 passed in 0.24s
```

## Pruebas HTTP manuales

Servidor reiniciado con:

```bash
.venv/bin/python server.py
```

Estado:

```bash
curl -s http://localhost:8765/api/status
```

Resultado:

```json
{"status":"ok","ok":true,"can_search":true,"gmail_lib":true,"credentials":true,"token":true,"msg":"Token disponible"}
```

UI:

```bash
curl -s http://localhost:8765/
```

Resultado: sirve `index.html` y mantiene `const API = ''`.

Error controlado:

```bash
curl -s 'http://localhost:8765/api/search?sender=&max=abc'
```

Resultado:

```json
{"status":"error","error":"Parámetro sender requerido","detail":"Indica un dominio o email"}
```

## Cobertura añadida

- Validacion de `max`.
- Validacion de dominios y emails.
- Normalizacion de fechas Gmail.
- Etiquetas derivadas del remitente.
- Decodificacion de snippets Gmail.
- Normalizacion de mensajes Gmail metadata.
- Clasificacion de categorias.
- Respuestas JSON y errores API sin Gmail real.

## Pruebas no ejecutadas

- Busqueda Gmail real desde UI tras la modularizacion.

## Riesgo residual

- `classifier.py` duplica reglas que tambien existen en `index.html`; una fase posterior deberia evitar divergencia o generar ambas desde una fuente comun.
