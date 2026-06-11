# Gestor de Correos — Servidor Local

## What This Is

Herramienta local para consultar Gmail y convertir correos técnicos de infraestructura en una vista accionable. Está orientada a gestionar avisos de Vultr, Plesk, servidor, dominios, SSL, facturación, mantenimiento y seguridad desde una interfaz web servida por Python.

## Core Value

Detectar y priorizar correos técnicos importantes sin exponer datos de Gmail fuera del equipo local.

## Credits

- **Creator:** EDF Developer
- **User:** edefrutos

## Requirements

### Validated

- [x] Servidor local sirve una interfaz HTML en `http://localhost:8765`.
- [x] La app puede autenticarse con Gmail API en modo readonly.
- [x] La UI permite filtrar, categorizar, seleccionar, exportar y ocultar correos.
- [x] Se pueden añadir remitentes/dominios y buscar mensajes reales en Gmail.

### Validated in v1

- [x] Responsabilidades separadas entre servidor, Gmail, clasificación y almacenamiento.
- [x] Persistencia local para fuentes, ocultados y preferencias.
- [x] Sistema de severidad, agrupación por proveedor y vista de acciones pendientes.
- [x] Exportación operativa Markdown/JSON.
- [x] Escala tipográfica contextual legible en escritorio y móvil.
- [x] Suite automatizada para backend, Gmail, almacenamiento, validación y clasificación.

### Validated in v2

- [x] Reglas de clasificación editables desde la UI.
- [x] Resúmenes semanales o mensuales por proveedor y riesgo.
- [x] Detección de tendencias y fallos recurrentes.
- [x] Resumen opcional mediante proveedor AI compatible con OpenAI.
- [x] Frontend separado en estructura, estilos, aplicación principal y resúmenes.
- [x] Controles responsive contenidos sin desbordes horizontales conocidos.

### Validated in v3

- [x] Completar el ciclo de tratamiento de ocultos: restaurar, conservar ocultos o borrar permanentemente de Gmail.

### Validated in v4

- [x] Reutilizar la autorización destructiva válida entre sesiones sin repetir OAuth si el token sigue siendo válido.
- [x] Aumentar el número de ocultos que pueden borrarse en una sola operación manteniendo el perímetro hidden-only.
- [x] Conservar confirmación exacta, resultados por ID y auditoría local acotada para lotes grandes.

### Validated in v5

- [x] Revocar explícitamente `delete_token.json` desde la UI o la API sin tocar el resto del estado local.
- [x] Afinar la limpieza local de huérfanos para distinguir mejor entre ocultos disponibles, no localizables y ya desconectados de Gmail.
- [x] Mejorar el flujo operativo de mantenimiento para que la gestión destructiva y la limpieza local sean más claros y menos angustiantes.

## Current Milestone: v5.0 Destructive Revocation, Orphan Cleanup, and Operational Clarity

**Status:** Completed.
**Goal:** dar una salida explícita al scope destructivo, refinar la limpieza local de huérfanos y hacer más clara la operativa de mantenimiento sin abrir nuevas escrituras generales en Gmail.
**Result:** phases 16, 17 y 18 completed; revocación explícita del token destructivo disponible desde UI/API con estado `revoked` persistente, limpieza local de huérfanos distinguida entre disponibles, no localizables y desconectados, y flujo operativo separado para acciones locales y acciones que afectan a Gmail.

**Target features:**
- La UI ofrece una revocación explícita del token destructivo y el estado de la API refleja con claridad el cambio.
- La limpieza local de huérfanos distingue mensajes disponibles, no localizables y ya desconectados de Gmail.
- La experiencia de mantenimiento reduce fricción y ambigüedad al tratar ocultos, tokens y limpieza local.

### Out of Scope

- Multiusuario público — el proyecto debe seguir local-first hasta tener seguridad formal.
- Escritura Gmail general — archivar, etiquetar o modificar mensajes visibles sigue fuera del alcance.
- Migración inmediata a React/Next.js — la UI actual puede evolucionar antes de introducir build tooling.

## Context

El proyecto está modularizado en `server.py`, `gmail_client.py`, `destructive_gmail.py`, `validators.py`, `classifier.py`, `storage.py` y `ai_client.py`. El frontend separa estructura (`index.html`), estilos (`static/app.css`), comportamiento principal (`static/app.js`) y resúmenes/tendencias/AI (`static/summary.js`). V3 a v5 completaron la bandeja paginada de ocultos, la autorización destructiva separada y revocable, lotes de hasta 100 IDs, limpieza de huérfanos y claridad operativa. `credentials.json`, `token.json`, `delete_token.json` y `app_state.json` deben tratarse como privados.

## Constraints

- **Privacidad:** la lectura normal debe permanecer en `gmail.readonly`; el permiso destructivo completo sólo puede activarse de forma explícita y aislada.
- **Destrucción:** el borrado permanente debe limitarse a mensajes previamente ocultos, con confirmación reforzada y sin rutas implícitas.
- **Ejecución:** la herramienta debe funcionar con `.venv/bin/python server.py` en macOS sin infraestructura externa.
- **Seguridad:** ninguna web externa debe poder consultar la API local.
- **Simplicidad:** evitar frameworks y build tooling mientras la arquitectura estática actual siga siendo suficiente.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mantener local-first | Minimiza exposición de datos privados y simplifica OAuth | ✓ Good |
| Priorizar seguridad antes de nuevas funciones | La API local tiene acceso a Gmail autenticado | ✓ Done |
| Usar persistencia local antes de cloud | Preferencias y estados deben sobrevivir sin servidor externo | ✓ Done |
| Mantener lectura Gmail readonly | Reduce riesgo operativo para todas las operaciones normales | ✓ Good |
| Mantener frontend sin build tooling | La separación actual permite evolucionar sin introducir complejidad operativa | ✓ Good |
| Aislar borrado permanente | Evita que el cliente normal mantenga permisos destructivos completos | ✓ Done |
| Reutilizar autorización destructiva válida entre sesiones | Evita repetir OAuth si el token sigue siendo válido y reduce fricción operativa | ✓ Done |
| Añadir revocación explícita del token destructivo | Da una salida clara y segura para cerrar la ventana de un scope sensible | ✓ Done |
| Mantener fijo el lote máximo en 100 | Evita ambigüedad operativa y mantiene el contrato destructivo estable | ✓ Decided |
| Convertir la limpieza de huérfanos en un flujo de mantenimiento más claro | Evita que IDs desconectados se confundan con mensajes aún gestionables | ✓ Decided |
| Retirar el pool `BASE` incrustado | Evita almacenar contenido Gmail en el código y que mensajes inexistentes reaparezcan tras recargar | ✓ Done |

---
*Last updated: 2026-06-11 after completing phase 18 of v5.0*
