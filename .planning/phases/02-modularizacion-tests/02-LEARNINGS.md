---
phase: 02
phase_name: "modularizacion-tests"
project: "Gestor de Correos — Servidor Local"
generated: "2026-06-01"
counts:
  decisions: 5
  lessons: 4
  patterns: 5
  surprises: 3
missing_artifacts:
  - "02-UAT.md"
---

# Phase 02 Learnings: modularizacion-tests

## Decisions

### Mantener `server.py` como capa HTTP fina
`server.py` quedo centrado en servir `index.html`, enrutar `/api/status` y `/api/search`, y emitir respuestas JSON.

**Rationale:** La fase buscaba que la logica critica dejara de vivir en un unico archivo y pudiera testearse en modulos separados.
**Source:** 02-SUMMARY.md

---

### Concentrar Gmail y OAuth en `gmail_client.py`
OAuth, estado Gmail, normalizacion de fechas, tags, mensajes y busqueda se movieron a `gmail_client.py`.

**Rationale:** Separar acceso Gmail del servidor HTTP reduce acoplamiento y facilita tests sobre helpers sin levantar servidor.
**Source:** 02-SUMMARY.md

---

### Concentrar validacion API en `validators.py`
`ApiError`, `parse_max(raw)` y `validate_sender(raw)` se extrajeron a `validators.py`.

**Rationale:** La validacion de parametros es logica critica compartible y testeable, y no debe quedar mezclada con routing HTTP.
**Source:** 02-SUMMARY.md

---

### Mantener el frontend sin cambios funcionales
La fase no cambio funcionalmente `index.html`.

**Rationale:** El alcance era modularizar backend y añadir pruebas sin introducir regresiones ni redisenar la UI.
**Source:** 02-SUMMARY.md

---

### No probar contra Gmail real en tests automatizados
Los tests de API simulan Gmail y errores con monkeypatch.

**Rationale:** La suite debe ser rapida, repetible y no debe abrir OAuth ni depender de red, token o configuracion externa.
**Source:** 02-SUMMARY.md

---

## Lessons

### Separar modulos permite probar sin tocar OAuth
La suite cubre validacion, fechas, tags, normalizacion, clasificacion y respuestas API sin llamar a Gmail real.

**Context:** `tests/test_server_api.py` usa monkeypatch para simular Gmail y errores; `tests/test_gmail_client.py` prueba helpers puros.
**Source:** 02-VERIFICATION.md

---

### La modularizacion puede dejar duplicacion temporal
`classifier.py` duplica reglas que tambien existen en `index.html`.

**Context:** La verificacion documenta que una fase posterior deberia evitar divergencia o generar ambas reglas desde una fuente comun.
**Source:** 02-VERIFICATION.md

---

### `pytest` debe formar parte de las dependencias del proyecto
`pytest` se anadio a `requirements.txt` y se instalo en `.venv`.

**Context:** La verificacion registra `.venv/bin/python -m pip install -r requirements.txt` como paso necesario para ejecutar la suite.
**Source:** 02-VERIFICATION.md

---

### Mantener mensajes JSON en espanol evita romper la UI
La fase conservo los mensajes API existentes en espanol.

**Context:** El summary lo documenta como decision para no cambiar contratos visibles consumidos por el frontend.
**Source:** 02-SUMMARY.md

---

## Patterns

### Capa HTTP fina
El servidor HTTP se limita a parsing de rutas, respuesta JSON, archivos estaticos y delegacion a modulos.

**When to use:** En apps locales pequenas donde se quiere mantener `http.server` pero hacer testeable la logica de negocio.
**Source:** 02-SUMMARY.md

---

### Modulos por responsabilidad
Gmail/OAuth, validacion y clasificacion viven en archivos separados.

**When to use:** Cuando un archivo unico empieza a mezclar integracion externa, reglas de negocio y transporte HTTP.
**Source:** 02-PLAN.md

---

### Tests sin servicios externos
Los tests de API simulan Gmail y errores en vez de llamar a la API real.

**When to use:** En integraciones OAuth/API donde la suite debe correr sin credenciales, red ni ventanas de autorizacion.
**Source:** 02-SUMMARY.md

---

### Verificacion combinada: compile, pytest y HTTP smoke tests
La fase usa `py_compile`, `pytest` y pruebas HTTP manuales de `/api/status`, `/` y errores de `/api/search`.

**When to use:** En refactors de arquitectura que no deberian cambiar comportamiento visible.
**Source:** 02-VERIFICATION.md

---

### Documentar riesgo residual explicitamente
La duplicacion de reglas entre `classifier.py` e `index.html` quedo registrada como riesgo residual.

**When to use:** Cuando una fase mejora una frontera tecnica pero deja una inconsistencia conocida para una fase posterior.
**Source:** 02-VERIFICATION.md

---

## Surprises

### La cobertura automatizada llego a 31 tests sin tocar Gmail real
La suite final cubre validadores, helpers Gmail, clasificacion y API con 31 tests pasando.

**Impact:** La base queda preparada para refactors posteriores con menos riesgo, sin depender de credenciales ni Google Cloud.
**Source:** 02-VERIFICATION.md

---

### El mayor riesgo residual no esta en el backend sino en la duplicacion con la UI
Aunque el backend quedo modularizado, las categorias existen tanto en Python como en JavaScript.

**Impact:** Cambios futuros de reglas pueden divergir entre tests backend y comportamiento real de la UI si no se centralizan.
**Source:** 02-VERIFICATION.md

---

### La prueba manual de busqueda Gmail real quedo fuera de la verificacion de fase
Tras la modularizacion no se ejecuto busqueda Gmail real desde la UI.

**Impact:** La fase queda verificada por tests y smoke tests HTTP, pero conviene mantener una prueba manual de remitente real antes de cambios de persistencia.
**Source:** 02-VERIFICATION.md
