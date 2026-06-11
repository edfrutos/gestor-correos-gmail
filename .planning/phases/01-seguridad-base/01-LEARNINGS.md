---
phase: 01
phase_name: "seguridad-base"
project: "Gestor de Correos — Servidor Local"
generated: "2026-06-01"
counts:
  decisions: 5
  lessons: 5
  patterns: 5
  surprises: 4
missing_artifacts:
  - "01-UAT.md"
---

# Phase 01 Learnings: seguridad-base

## Decisions

### Mantener una aplicacion local sin build tooling
La fase mantuvo `server.py` como servidor local y `index.html` como UI completa, sin introducir frameworks ni build tooling.

**Rationale:** El objetivo era endurecer la herramienta sin cambiar su propuesta de uso ni ampliar el alcance de la fase.
**Source:** 01-SUMMARY.md

---

### Servir UI y API desde el mismo origen
Se elimino el CORS abierto y la UI debe servirse desde `http://localhost:8765`.

**Rationale:** La UI y la API comparten origen local, asi que no hace falta permitir consultas desde webs externas.
**Source:** 01-SUMMARY.md

---

### Separar estado pasivo de autenticacion OAuth
`/api/status` informa dependencias, `credentials.json` y `token.json` sin llamar a Gmail ni abrir OAuth.

**Rationale:** Consultar estado no debe tener efectos secundarios ni abrir navegador; la autenticacion queda diferida a una busqueda explicita.
**Source:** 01-SUMMARY.md

---

### Usar entorno virtual local para dependencias
La instalacion se ajusto a `.venv` y la ejecucion documentada paso a `.venv/bin/python server.py`.

**Rationale:** El Python de Homebrew bloqueo la instalacion global por PEP 668, asi que `.venv` evita modificar el entorno del sistema.
**Source:** 01-VERIFICATION.md

---

### Mantener Gmail en modo readonly
La integracion conserva el scope `https://www.googleapis.com/auth/gmail.readonly`.

**Rationale:** La fase solo consulta, localiza, filtra, exporta y oculta en la vista local; escribir en Gmail queda fuera de v1.
**Source:** .planning/STATE.md

---

## Lessons

### No ocultar errores de Gmail como listas vacias
El backend devolvia listas vacias cuando Gmail fallaba, lo que hacia parecer que la busqueda funcionaba pero no encontraba correos.

**Context:** Al exponer el error real, se detecto que Gmail API estaba desactivada en el proyecto Google Cloud asociado a `credentials.json`.
**Source:** 01-VERIFICATION.md

---

### Buscar remitentes no equivale a importar solo correos nuevos
La busqueda de remitentes debe localizar mensajes tratables aunque ya estuvieran cargados en memoria.

**Context:** La UI se ajusto para filtrar la vista por el dominio localizado y permitir seleccion, exportacion y ocultado aunque no hubiera mensajes nuevos.
**Source:** 01-VERIFICATION.md

---

### El estado `ok` no prueba por si solo una busqueda Gmail real
`/api/status` puede confirmar dependencias, credenciales y token, pero la busqueda real puede fallar por configuracion externa de Google Cloud.

**Context:** Tras instalar dependencias y tener token disponible, `/api/search` todavia devolvia error hasta activar Gmail API en el proyecto.
**Source:** 01-VERIFICATION.md

---

### PEP 668 afecta al flujo de instalacion en macOS con Homebrew
La instalacion global con `pip install -r requirements.txt` fallo porque el entorno Python estaba gestionado externamente.

**Context:** La solucion documentada fue crear `.venv` e instalar ahi las dependencias de Google.
**Source:** 01-VERIFICATION.md

---

### La sanitizacion debe preservar enlaces utiles
Endurecer HTML dinamico no podia limitarse a escapar todo sin mas, porque los cuerpos de correo pueden contener enlaces utiles.

**Context:** El plan ya identificaba el riesgo de no degradar enlaces utiles; la implementacion valida URL antes de crear anchors.
**Source:** 01-PLAN.md

---

## Patterns

### Endpoint de estado sin efectos secundarios
`/api/status` debe limitarse a inspeccionar estado local y no llamar a servicios externos.

**When to use:** En herramientas locales con OAuth, cuando una comprobacion de salud no debe disparar login ni modificar token.
**Source:** 01-SUMMARY.md

---

### Errores API con `status`, `error` y `detail`
Las respuestas de error se normalizaron como JSON estructurado.

**When to use:** En endpoints locales consumidos por una UI que necesita mostrar errores accionables sin parsear trazas ni texto arbitrario.
**Source:** 01-SUMMARY.md

---

### Validacion temprana de parametros de busqueda
`sender` se valida como dominio/email simple y `max` se limita al rango 1..100 antes de consultar Gmail.

**When to use:** En cualquier endpoint que construya consultas hacia APIs externas a partir de input de usuario.
**Source:** 01-SUMMARY.md

---

### Localizacion de remitente como filtro operativo
Cuando una busqueda Gmail devuelve correos, la UI activa o reutiliza la fuente, filtra la lista por dominio y deja acciones disponibles.

**When to use:** En interfaces donde buscar es una accion de trabajo sobre resultados, no solo una importacion incremental.
**Source:** 01-VERIFICATION.md

---

### Documentar instalacion con entorno virtual
La documentacion operativa usa `.venv/bin/python` tanto para instalar como para ejecutar.

**When to use:** En proyectos Python locales sobre macOS/Homebrew para evitar errores de entorno gestionado y diferencias entre interpretes.
**Source:** 01-VERIFICATION.md

---

## Surprises

### Gmail API estaba desactivada aunque habia credenciales y token
La app tenia `credentials.json`, token OAuth y dependencias instaladas, pero Google devolvia 403 porque Gmail API no estaba activada en el proyecto.

**Impact:** La busqueda real no podia funcionar hasta activar Gmail API en Google Cloud; exponer el error real fue necesario para diagnosticarlo.
**Source:** 01-VERIFICATION.md

---

### El Python del sistema no era el entorno correcto para la app
El servidor activo inicialmente usaba un Python sin dependencias de Gmail aunque el proyecto ya tenia archivos de configuracion.

**Impact:** La UI mostraba que faltaban dependencias y no podia buscar; hizo falta crear `.venv`, instalar dependencias y reiniciar con `.venv/bin/python server.py`.
**Source:** 01-VERIFICATION.md

---

### Los remitentes vacios podian incorporarse tras fallos de busqueda
La UI interpretaba un fallo como cero correos y anadia la fuente con contador 0.

**Impact:** Aparecian chips de remitentes sin mensajes tratables, confundiendo el flujo de seleccion, exportacion y ocultado.
**Source:** 01-SUMMARY.md

---

### Cambiar CORS obliga a usar siempre la UI servida por el servidor
Eliminar CORS abierto implica que abrir `index.html` como archivo local puede romper pruebas.

**Impact:** La verificacion y el uso operativo deben hacerse desde `http://localhost:8765`.
**Source:** 01-PLAN.md
