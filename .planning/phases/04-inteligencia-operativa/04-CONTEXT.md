# Phase 4: Inteligencia Operativa - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 turns the current Gmail helper into an operational decision panel: a single prioritized queue of actionable emails, fixed severity rules, primary grouping by provider/sender, and clean exports in Markdown or JSON. It must stay local-first and Gmail readonly; local hide remains `Ocultar` and does not mutate Gmail.

</domain>

<decisions>
## Implementation Decisions

### Bandeja de acciones pendientes
- **D-01:** The main view is a single actionable queue, not separate inboxes by action type.
- **D-02:** Items in that queue are ordered by priority, with severity as the main sorting signal.
- **D-03:** The queue should surface only emails that require action or review; it is not a raw mailbox mirror.

### Severidad
- **D-04:** Severity is fixed by category with three levels: `alta`, `media`, `baja`.
- **D-05:** Severity is not manually edited per email in Phase 4.
- **D-06:** The severity model should remain deterministic so the same message gets the same level from the same rules.

### Agrupación
- **D-07:** The primary grouping is by remitente/proveedor.
- **D-08:** Other groupings can exist as secondary presentation details, but provider grouping is the main organizing lens for the phase.

### Exportación
- **D-09:** Export both Markdown and JSON.
- **D-10:** The user chooses at export time whether to export the current filtered view or the full set.
- **D-11:** Exported output should be clean and operational: summary, source, date, category, severity, and Gmail link.

### the agent's Discretion
- Decide the exact severity rule table per category, provided it stays fixed and explainable.
- Decide the exact shape of the Markdown and JSON exports, provided both are clean and consistent.
- Decide whether the actionable queue and grouped provider view are tabs, sections, or a toggle, provided the primary grouping remains by provider.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Rules
- `.planning/PROJECT.md` — Defines the local-first product boundary, privacy constraints, and core value.
- `.planning/REQUIREMENTS.md` — Defines `PROD-01`, `PROD-03`, and `PROD-04`, which anchor this phase.
- `.planning/ROADMAP.md` — Defines Phase 4 scope, outcome, and verification expectations.
- `.planning/STATE.md` — Captures the current project focus and recent operational context.
- `AGENTS.md` — Repository conventions, security notes, and manual verification expectations.
- `README.md` — Local setup and execution notes for the current app.

### Prior Phase Context
- `.planning/phases/03-persistencia-local/03-CONTEXT.md` — Locks the persistence and local-hide semantics that Phase 4 must preserve.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `classifier.py`: Already classifies emails into semantic categories; Phase 4 can extend the same rule-driven approach for severity instead of inventing a second classifier.
- `index.html`: Already renders cards, badges, attachments, selection, local hide, and export controls in a single-page UI; this is the main surface for the queue and grouping changes.
- `server.py`: Already exposes `/api/search`, `/api/state`, `/api/message`, and `/api/attachment`; Phase 4 can keep the same local HTTP boundary and enrich the data flowing through it.
- `gmail_client.py`: Already normalizes Gmail messages and attachments into stable local objects with `id`, `date`, `subject`, `from`, `snippet`, and `attachments`.
- `storage.py`: Already persists local sources, hidden IDs, and UI preferences; this can hold Phase 4 filters or view preferences if needed.
- `validators.py`: Already centralizes API input validation and can be reused for any new query or export parameters.
- `tests/test_server_api.py`, `tests/test_classifier.py`, `tests/test_storage.py`, `tests/test_gmail_client.py`: Existing test coverage patterns are ready to extend for severity, grouping, and export behavior.

### Established Patterns
- Gmail remains readonly; local actions only change the app's view and persisted local state.
- User-facing text is Spanish, while internal code and APIs stay compact and deterministic.
- The frontend is still a single HTML file with imperative rendering and explicit state hydration from the server.
- API errors are returned as JSON with a simple `{status, error, detail}` shape.

### Integration Points
- Severity and queue ordering belong close to `classifier.py` and the data flow that builds each email record.
- Grouping and action-pending views belong in `index.html` render logic, reusing the existing card/list rendering path.
- Export belongs in the frontend action bar, but the exported data should come from the same normalized message model used by the server.
- Any new export or queue metadata should avoid storing Gmail content in `app_state.json`; state remains preference-oriented only.

</code_context>

<specifics>
## Specific Ideas

- The queue should be flat and priority-driven.
- Severity is category-based and fixed, not hand-tuned per message.
- Provider/sender is the primary grouping axis.
- Export format is both Markdown and JSON.
- Export scope is decided at the moment of export, not as a global setting.

</specifics>

<deferred>
## Deferred Ideas

- Manual per-email severity editing.
- Separate action-type inboxes.
- Gmail write actions such as labels, archive, or delete.
- Weekly or monthly operational summaries.
- Editable classification rules from the UI if they expand beyond the fixed category severity table.

</deferred>

---

*Phase: 4-Inteligencia Operativa*
*Context gathered: 2026-06-01*
