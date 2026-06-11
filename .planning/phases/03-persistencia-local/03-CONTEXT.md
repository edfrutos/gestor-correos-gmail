# Phase 3: Persistencia Local - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers local persistence for the existing Gmail helper state: added sender sources, locally hidden email IDs, and basic UI preferences. The app remains local-first and Gmail readonly. This phase must not add Gmail write actions, remote storage, user accounts, or the Phase 4 operational intelligence features.

</domain>

<decisions>
## Implementation Decisions

### Storage Format
- **D-01:** Use a local JSON state file for Phase 3 persistence.
- **D-02:** Keep the format simple, inspectable, and dependency-free. SQLite is deferred until the app needs larger history, richer querying, or report-oriented storage.

### Persisted State
- **D-03:** Persist configuration/state only: custom sender sources, hidden email IDs, and basic preferences.
- **D-04:** Do not cache Gmail message snippets or message bodies in Phase 3. Matching emails should continue to be located through Gmail when needed.
- **D-05:** Fixed built-in sources remain code-defined; persisted sources should cover user-added sources only.

### Hidden Email Semantics
- **D-06:** "Borrar" remains a local hide action. It must not delete, archive, label, or otherwise mutate Gmail.
- **D-07:** Hidden emails should survive browser reload and server restart.
- **D-08:** Hidden emails must be restorable through a clear local recovery/reset path, rather than becoming permanently invisible without editing the state file.

### API/UI Boundary
- **D-09:** Add persistence through the existing local Python server, not browser-only `localStorage`, so state survives browser changes and server restart consistently.
- **D-10:** The frontend should hydrate state from the server during startup and save state after relevant changes.

### the agent's Discretion
- Choose the exact JSON filename and schema, provided secrets are not mixed with app state and the file is documented/ignored appropriately.
- Choose whether persistence uses granular endpoints or a single state endpoint, provided tests cover validation and error behavior.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning
- `.planning/PROJECT.md` — Defines the local-first, Gmail-readonly product boundary and privacy constraints.
- `.planning/REQUIREMENTS.md` — Defines `ARCH-03` and `PROD-02`, the requirements owned by Phase 3.
- `.planning/ROADMAP.md` — Defines Phase 3 scope and verification expectations.
- `.planning/STATE.md` — Captures current focus, risks, and prior operational context.

### Prior Phase Artifacts
- `.planning/phases/02-modularizacion-tests/02-SUMMARY.md` — Defines current module boundaries after Phase 2.
- `.planning/phases/02-modularizacion-tests/02-LEARNINGS.md` — Notes residual frontend/backend duplication and test strategy.

### Repository Guidance
- `AGENTS.md` — Repository conventions, security notes, and manual verification expectations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server.py`: Thin HTTP layer already serving `/api/status` and `/api/search`; persistence endpoints should fit this route-handler pattern.
- `validators.py`: Existing `ApiError` pattern can be reused for state payload validation failures.
- `tests/test_server_api.py`: Dummy handler and monkeypatch style are established for endpoint tests without starting the server.
- `index.html`: Existing state variables (`customSrcs`, `deleted`, `cf`, `cq`, `activeCat`) identify the client state that needs hydration/save behavior.

### Established Patterns
- Backend tests avoid Gmail real calls and monkeypatch external dependencies.
- Gmail data remains readonly; local treatment actions affect only the app's view.
- User-facing API errors are JSON and Spanish-language.
- The frontend is still a single HTML file; Phase 3 should keep changes focused and avoid new build tooling.

### Integration Points
- Add a backend storage module rather than expanding Gmail logic or overloading `server.py`.
- Add one or more `/api/state` endpoints in `server.py` for loading and saving persisted state.
- Hydrate state in `index.html` before initial rendering, then persist after adding/removing sources, hiding/restoring emails, and preference changes.
- Update `.gitignore` and documentation so generated local state is not committed.

</code_context>

<specifics>
## Specific Ideas

- Preferred implementation direction: JSON local + no Gmail email cache + locally restorable hidden emails.
- The visible UI already tells the user deletion does not affect Gmail; Phase 3 should preserve that mental model.

</specifics>

<deferred>
## Deferred Ideas

- SQLite storage can be reconsidered when Phase 4 grouping, reporting, or longer-lived analytics make querying/history valuable.
- Gmail write actions such as archiving, deleting, or labeling remain out of scope until a future phase explicitly approves broader OAuth scopes.
- Persisting editable classification rules is mentioned in the roadmap outcome, but rule editing itself is a later capability unless planning finds a minimal config-only representation required by `PROD-02`.
- Attachment indicators and opening attachments belong to Phase 4 (`PROD-05`) because they change email treatment/display rather than local persistence.

</deferred>

---

*Phase: 3-Persistencia Local*
*Context gathered: 2026-06-01*
