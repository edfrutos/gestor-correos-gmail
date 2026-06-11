# Phase 4: Inteligencia Operativa - Research

**Gathered:** 2026-06-01
**Status:** Research complete

## Technical Findings

### Frontend architecture
- The app is still a single `index.html` with imperative DOM rendering and inline CSS/JS.
- Existing interactive flows already handle status, sender search, category chips, selection, hidden recovery, attachment opening, and export modal behavior.
- The current export modal already supports multiple formats and a download/copy flow, so Phase 4 can reuse that pattern instead of introducing a new page or framework.

### Backend and data flow
- `server.py` remains a thin HTTP layer with JSON endpoints and Gmail helpers.
- `gmail_client.py` already normalizes Gmail messages into a stable object shape with `id`, `date`, `from`, `to`, `subject`, `snippet`, `attachments`, and `tag`.
- `classifier.py` is the natural place to keep deterministic category/severity rules because it already holds the semantic classification logic.
- `storage.py` persists local UI state only; Phase 4 should not move export data or message bodies into `app_state.json`.

### Existing export behavior
- Export currently happens entirely in the frontend from the already loaded `activeEmails`.
- The export modal already lets the user choose output format and copy/download the generated result.
- Current export grouping is by subject; Phase 4 can replace that with the new provider-first operational grouping without needing new backend endpoints.

### Practical implications
- A client-side export implementation is still sufficient for Phase 4 because all required fields are already present in the UI model.
- Markdown and JSON exports can be generated from the same normalized email collection.
- The phase can remain readonly on Gmail; local actions and exports only affect the app view and local files.

## Reusable Code Paths

- `classifier.py` for category/severity decisions.
- `index.html` render and export functions.
- `server.py` and `gmail_client.py` for normalized email data and Gmail links.
- `tests/test_classifier.py`, `tests/test_gmail_client.py`, and `tests/test_server_api.py` as the starting point for coverage.

## Constraints Confirmed

- No new framework is needed for Phase 4.
- Gmail remains readonly.
- Export must not persist Gmail content locally beyond the current in-memory UI state.
- The UI must remain compact, dark, and operational rather than marketing-like.
