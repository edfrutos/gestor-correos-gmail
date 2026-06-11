# Decisions

## ADR-001 — Mantener Ejecución Local

**Date:** 2026-05-31  
**Status:** Accepted

La herramienta seguirá ejecutándose en local mediante `.venv/bin/python server.py`.

**Rationale:** Gmail contiene datos privados y el valor actual no requiere despliegue público. Mantenerla local reduce superficie de ataque, coste operativo y complejidad de autenticación.

**Consequences:** cualquier API local debe tratarse como sensible. No se debe abrir CORS de forma indiscriminada. Las dependencias Python se instalan en `.venv` para evitar modificar el Python de Homebrew.

## ADR-002 — Gmail Readonly por Defecto

**Date:** 2026-05-31  
**Status:** Accepted

La integración Gmail mantendrá `https://www.googleapis.com/auth/gmail.readonly`.

**Rationale:** la herramienta actual consulta, clasifica y exporta; no necesita modificar Gmail. Ampliar scopes obligaría a revisar seguridad y UX.

**Consequences:** archivar, borrar o etiquetar correos queda fuera de v1.

## ADR-003 — Seguridad Antes de Funcionalidad Nueva

**Date:** 2026-05-31  
**Status:** Accepted

La primera fase se centrará en CORS, validación, secretos y render seguro antes de añadir persistencia o inteligencia.

**Rationale:** la API local accede a Gmail autenticado; nuevas funciones sobre una base insegura amplificarían el riesgo.

**Consequences:** paneles avanzados, reglas editables y resúmenes quedan tras el hardening inicial.

## ADR-004 — Persistencia Local Antes que Cloud

**Date:** 2026-05-31  
**Status:** Accepted

La persistencia se implementa localmente mediante JSON normalizado y escritura atómica. SQLite queda como opción si el estado crece.

**Rationale:** fuentes, reglas, ocultados y preferencias necesitan sobrevivir entre sesiones sin exponer datos fuera del equipo.

**Consequences:** `app_state.json` guarda fuentes, reglas editables, IDs ocultos y preferencias, pero no contenido Gmail.

## ADR-005 — AI Opcional y Transmisión Explícita

**Date:** 2026-06-09
**Status:** Accepted

La integración AI permanece desactivada sin configuración y sólo recibe un resumen operativo cuando el usuario solicita la acción.

**Rationale:** cualquier proveedor remoto amplía la frontera de privacidad y debe ser una decisión visible, no un efecto secundario.

**Consequences:** la API key permanece en Python, los proveedores remotos requieren confirmación y Gmail nunca se envía automáticamente.

## ADR-006 — Frontend Modular sin Build Tooling

**Date:** 2026-06-09
**Status:** Accepted

La interfaz separa HTML, CSS, aplicación principal y resúmenes en activos estáticos servidos desde una lista cerrada.

**Rationale:** la separación reduce el coste de mantenimiento sin introducir un pipeline de compilación innecesario para una herramienta local.

**Consequences:** los activos nuevos deben añadirse explícitamente a `STATIC_FILES`; una migración a framework requiere una decisión posterior.

## ADR-007 — Borrado Permanente Aislado

**Date:** 2026-06-10
**Status:** Accepted

El tratamiento final de ocultos incluirá borrado inmediato, permanente e irreversible mediante `users.messages.delete`.

**Rationale:** el usuario ha elegido explícitamente borrar del servidor Gmail sin pasar por Papelera. Gmail exige para ello el scope restringido `https://mail.google.com/`; `gmail.modify` no permite esta operación.

**Consequences:** el cliente normal conservará `gmail.readonly`. El permiso destructivo usará un token separado, estará desactivado por defecto, sólo aceptará IDs actualmente ocultos, limitará cada lote a 20 mensajes y exigirá una frase de confirmación con el número exacto.

**Sources:**
- https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/delete
- https://developers.google.com/workspace/gmail/api/auth/scopes
