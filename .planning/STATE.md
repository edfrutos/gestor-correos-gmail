---
gsd_state_version: 1.0
milestone: v7.5
milestone_name: Local Reader, Persistent Exports and OS Integration
status: complete
last_updated: "2026-06-12T00:00:00Z"
progress:
  total_phases: 29
  completed_phases: 29
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-06-11)

**Core value:** Detectar y priorizar correos técnicos importantes sin exponer datos de Gmail fuera del equipo local.  
**Current focus:** Integración profunda con macOS (Servicios), lector EML integrado y gestión de exportaciones locales terminada.

## Current Status

v1 a v7.5 implementadas. La herramienta es ahora una estación de trabajo completa para Gmail y archivos EML locales.

## Last Activity

2026-06-12 — Implementada Phase 29: Lector EML integrado, directorio persistente `/exports` e integración con Servicios de macOS ("Acciones rápidas").
2026-06-12 — Implementada Phase 28: Sugerencias AI de reglas basadas en acciones locales (estrictamente opcional).
2026-06-12 — Implementadas Phase 26-27: Auto-etiquetado y Auto-archivado vinculados a reglas personalizadas con optimización de llamadas API.
2026-06-12 — Implementadas Phase 24-25.1: Gestión completa de Gmail (archivar, listar/aplicar etiquetas y creación dinámica de etiquetas).
2026-06-12 — Implementada Phase 23: Búsqueda avanzada por fechas (after/before) y texto literal en Gmail, con rediseño del panel de búsqueda.
2026-06-12 — Implementada Phase 22: Unificación de reglas y categorías en el backend (`classifier.py`), hidratadas dinámicamente en el frontend.
2026-06-12 — Implementada Phase 21: Buscador integrado en el modal de Gestión de Ocultos mediante intersección con la API de Gmail.
2026-06-12 — Implementada Phase 20: Despliegue remoto seguro vía VPN, configuración por entorno, modo headless y soporte para `.env`.
2026-06-12 — Implementada Phase 19: Exportación de contenido completo en formato .eml (individual) y .zip (lotes).
2026-06-11 — Milestone v5.0 completado: revocación explícita, limpieza de huérfanos y refinamiento visual.

## Known Risks

- `credentials.json`, `token.json`, `delete_token.json` y `app_state.json` deben permanecer fuera de Git.
- La elevación a `gmail.modify` permite acciones de escritura; el borrado permanente sigue bajo una frontera destructiva adicional (`https://mail.google.com/`).
- Las sugerencias de IA envían metadatos (asunto/remitente) a un proveedor externo si el usuario habilita la opción.

## Next Recommended Action

La aplicación ha alcanzado su madurez funcional según los requisitos iniciales y extendidos. Se recomienda realizar una auditoría de rendimiento sobre lotes de archivado muy grandes (>100) y considerar el soporte multi-cuenta como futura expansión.
