# Phase 4: Inteligencia Operativa - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 04-inteligencia-operativa
**Areas discussed:** Bandeja de acciones pendientes, Severidad, Agrupación principal, Exportación, Export scope

---

## Bandeja de acciones pendientes

| Option | Description | Selected |
|--------|-------------|----------|
| Cola única priorizada | Una sola cola de correos accionables ordenada por prioridad. | ✓ |
| Bandejas por tipo | Bandejas separadas para renovar, pagar, revisar, informar. | |
| Vista por remitente | Agrupa por proveedor con acciones dentro de cada grupo. | |

**User's choice:** 1a
**Notes:** The view should be a single prioritized queue, not multiple inboxes by action type.

---

## Severidad

| Option | Description | Selected |
|--------|-------------|----------|
| Fija por categoría | Severidad alta/media/baja derivada de la categoría. | ✓ |
| Categoría + contexto | Ajusta severidad según fecha límite, adjuntos o urgencia. | |
| Manual por correo | Permite editar severidad caso a caso. | |

**User's choice:** 2a
**Notes:** The severity model must stay deterministic and explainable.

---

## Agrupación principal

| Option | Description | Selected |
|--------|-------------|----------|
| Remitente/proveedor | El eje principal es el proveedor o remitente. | ✓ |
| Categoría semántica | La agrupación principal es la categoría detectada. | |
| Fecha/mes | Agrupa por periodo temporal. | |

**User's choice:** 3a
**Notes:** Provider grouping is the main organizing lens for the phase.

---

## Exportación

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown + JSON | Exporta ambos formatos. | ✓ |
| Solo Markdown | Un único formato textual. | |
| Solo JSON | Un único formato estructurado. | |

**User's choice:** 4c
**Notes:** Both export formats are required.

---

## Export scope

| Option | Description | Selected |
|--------|-------------|----------|
| Vista filtrada actual | Exporta sólo lo que el usuario está viendo. | |
| Todo el conjunto | Exporta todos los correos del panel. | |
| Preguntar al exportar | El usuario decide en ese momento. | ✓ |

**User's choice:** 5c
**Notes:** Export scope must be chosen at the time of export.

---

## the agent's Discretion

- Exact severity mapping table per category.
- Exact structure of the Markdown and JSON exports.
- Exact UI shape for queue vs grouped provider presentation.

## Deferred Ideas

- Manual severity editing per message.
- Separate inboxes by action type.
- Gmail write actions (labels, archive, delete).
- Weekly or monthly summaries.
- Editable rules from the UI if scope grows later.
