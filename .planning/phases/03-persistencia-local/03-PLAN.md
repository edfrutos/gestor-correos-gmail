---
phase: 03
plan_id: 03-PLAN
title: Persistencia Local
wave: 1
depends_on: []
requirements_addressed: [ARCH-03, PROD-02]
files_modified:
  - storage.py
  - server.py
  - index.html
  - .gitignore
  - README.md
  - tests/test_storage.py
  - tests/test_server_api.py
autonomous: true
---

# Phase 3 Plan: Persistencia Local

## Objective

Persist local app state across browser reloads and server restarts using a project-local JSON file, without caching Gmail message content or changing the readonly Gmail contract.

## Must Haves

- Use local JSON storage, not SQLite.
- Persist only user-added sources, hidden email IDs, and basic preferences.
- Do not persist Gmail bodies, snippets, subjects, attachment contents, or other message cache.
- Keep "Borrar" as local hide only; Gmail must not be modified.
- Provide a clear UI path to restore hidden emails.
- Preserve `.venv/bin/python server.py` as the run command.

## Threat Model

- **Private data leakage:** State persistence must not become a Gmail data cache. Mitigation: whitelist state fields and reject/strip unknown Gmail message fields.
- **Local file corruption:** Interrupted writes must not leave invalid JSON. Mitigation: write to a temporary file and replace atomically.
- **Unexpected OAuth:** Loading local state must not trigger Gmail auth. Mitigation: `/api/state` must not import/use Gmail search; saved source refresh from UI must only run automatically when `/api/status` reports `token: true`.

## Tasks

<task id="03-01" name="Create local JSON storage module" type="execute">
  <read_first>
    <file>validators.py</file>
    <file>gmail_client.py</file>
    <file>.planning/phases/03-persistencia-local/03-CONTEXT.md</file>
    <file>.planning/phases/03-persistencia-local/03-RESEARCH.md</file>
  </read_first>
  <action>
    Create `storage.py` with `STATE_FILE = BASE_DIR / 'app_state.json'`, `DEFAULT_STATE`, `load_state()`, `save_state(raw_state)`, and `normalize_state(raw_state)`. The normalized schema must contain exactly `version`, `custom_sources`, `hidden_ids`, and `preferences`. Validate domains with the same domain rules as `validate_sender`; accept source objects with `dom`, `label`, and `color`; accept hidden IDs as bounded strings; accept preferences `source_filter`, `category_filter`, and `search_query`. Write atomically via a sibling temp file and `Path.replace()`.
  </action>
  <acceptance_criteria>
    <criterion>`storage.py` exists and defines `STATE_FILE`, `DEFAULT_STATE`, `load_state`, `save_state`, and `normalize_state`.</criterion>
    <criterion>`normalize_state({"custom_sources": [{"dom": "web.dev"}]})` returns a state with `version: 1` and no Gmail message fields.</criterion>
    <criterion>Invalid source domains raise `ApiError` with status 400.</criterion>
    <criterion>`save_state()` writes valid JSON and `load_state()` returns the saved normalized state.</criterion>
  </acceptance_criteria>
</task>

<task id="03-02" name="Add storage tests" type="execute">
  <read_first>
    <file>tests/test_validators.py</file>
    <file>tests/test_gmail_client.py</file>
    <file>storage.py</file>
  </read_first>
  <action>
    Create `tests/test_storage.py`. Cover default state when the file is missing, normalization of custom sources, rejection of invalid source domains, stripping/rejecting unknown Gmail cache fields, persistence of `hidden_ids`, persistence of `preferences`, and save/load roundtrip using a monkeypatched temporary `STATE_FILE`.
  </action>
  <acceptance_criteria>
    <criterion>`tests/test_storage.py` exists.</criterion>
    <criterion>Tests do not read or write the real `app_state.json`.</criterion>
    <criterion>`.venv/bin/python -m pytest tests/test_storage.py` exits 0.</criterion>
  </acceptance_criteria>
</task>

<task id="03-03" name="Expose state API endpoints" type="execute">
  <read_first>
    <file>server.py</file>
    <file>tests/test_server_api.py</file>
    <file>storage.py</file>
  </read_first>
  <action>
    Update `server.py` to import `load_state` and `save_state`. Add routing for `GET /api/state` and `POST /api/state`. Add request-body parsing using `Content-Length`, return JSON errors for malformed JSON or validation failures, and keep `/api/status` passive. Do not call `gmail()` or `search()` from state endpoints.
  </action>
  <acceptance_criteria>
    <criterion>`GET /api/state` returns JSON with `status: "ok"` and a `state` object.</criterion>
    <criterion>`POST /api/state` with a valid payload returns JSON with `status: "ok"` and normalized `state`.</criterion>
    <criterion>`POST /api/state` with malformed JSON returns a 400 JSON error.</criterion>
    <criterion>State endpoint tests prove `gmail()` is not called.</criterion>
    <criterion>`.venv/bin/python -m pytest tests/test_server_api.py` exits 0.</criterion>
  </acceptance_criteria>
</task>

<task id="03-04" name="Hydrate and persist frontend state" type="execute">
  <read_first>
    <file>index.html</file>
    <file>.planning/phases/03-persistencia-local/03-CONTEXT.md</file>
    <file>.planning/phases/03-persistencia-local/03-PATTERNS.md</file>
  </read_first>
  <action>
    Update `index.html` startup so it loads `/api/state` before initial render, applies `custom_sources` to `customSrcs`, applies `hidden_ids` to `deleted`, and applies preferences to `cf`, `cq`, and `activeCat`. Add a debounced `saveState()` that posts the current local state after adding/removing sources, hiding/restoring emails, and changing source/category/search preferences. Do not persist `activeEmails`, `selected`, `selMode`, message bodies, snippets, or subjects. Saved custom sources should render after reload; if `/api/status` reports `token: true`, refresh saved sources from Gmail without opening OAuth, otherwise wait for the user's explicit sender search.
  </action>
  <acceptance_criteria>
    <criterion>`index.html` contains a `loadState` or equivalent startup function that calls `/api/state` before the first final render.</criterion>
    <criterion>`index.html` contains a `saveState` or equivalent function that posts only sources, hidden IDs, and preferences.</criterion>
    <criterion>Adding a custom source triggers a state save after Gmail search completes.</criterion>
    <criterion>Removing a custom source triggers a state save.</criterion>
    <criterion>Changing source/category/search filters triggers a state save.</criterion>
    <criterion>Saved state payload does not include `body`, `snippet`, `subject`, `from`, `to`, or `cc`.</criterion>
  </acceptance_criteria>
</task>

<task id="03-05" name="Add hidden-email recovery UI" type="execute">
  <read_first>
    <file>index.html</file>
  </read_first>
  <action>
    Add a visible local hidden counter and a clear recovery action, using existing compact UI patterns. The recovery action must restore all hidden IDs by clearing `deleted`, saving state, re-rendering counts/cards, and showing a Spanish toast. Keep copy explicit that this does not affect Gmail.
  </action>
  <acceptance_criteria>
    <criterion>After hiding one email, the UI shows a hidden/oculto count greater than 0.</criterion>
    <criterion>Activating the recovery action clears `deleted` and posts state with an empty `hidden_ids` array.</criterion>
    <criterion>The recovery control is keyboard reachable as a native `button` or equivalent accessible control.</criterion>
    <criterion>The recovery copy states or implies local-only behavior, not Gmail deletion.</criterion>
  </acceptance_criteria>
</task>

<task id="03-06" name="Document local state and ignore generated file" type="execute">
  <read_first>
    <file>.gitignore</file>
    <file>README.md</file>
    <file>AGENTS.md</file>
  </read_first>
  <action>
    Add `app_state.json` to `.gitignore`. Update `README.md` to document `/api/state`, the local state file, what is persisted, what is not persisted, and how to reset local state by stopping the server and deleting `app_state.json`. Keep Spanish documentation concise and aligned with existing wording.
  </action>
  <acceptance_criteria>
    <criterion>`.gitignore` contains `app_state.json`.</criterion>
    <criterion>`README.md` documents `GET /api/state` and `POST /api/state`.</criterion>
    <criterion>`README.md` states that Gmail message bodies/snippets are not persisted.</criterion>
    <criterion>`README.md` explains how to reset local state.</criterion>
  </acceptance_criteria>
</task>

<task id="03-07" name="Run verification" type="execute">
  <read_first>
    <file>server.py</file>
    <file>storage.py</file>
    <file>validators.py</file>
    <file>gmail_client.py</file>
    <file>classifier.py</file>
    <file>tests/test_storage.py</file>
    <file>tests/test_server_api.py</file>
  </read_first>
  <action>
    Run syntax and pytest verification. Then run the server and manually verify reload/restart persistence for custom sources, hidden IDs, preferences, and hidden recovery.
  </action>
  <acceptance_criteria>
    <criterion>`.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py storage.py` exits 0.</criterion>
    <criterion>`.venv/bin/python -m pytest` exits 0.</criterion>
    <criterion>Manual: add a source, reload browser, source remains visible.</criterion>
    <criterion>Manual: hide an email, reload browser, email remains hidden.</criterion>
    <criterion>Manual: restart server, state remains loaded from `app_state.json`.</criterion>
    <criterion>Manual: restore hidden emails, reload browser, hidden count remains 0.</criterion>
    <criterion>Manual: inspect `app_state.json`; it contains no message bodies, snippets, subjects, or attachment data.</criterion>
  </acceptance_criteria>
</task>

## Verification Commands

```bash
.venv/bin/python -m py_compile server.py gmail_client.py validators.py classifier.py storage.py
.venv/bin/python -m pytest
.venv/bin/python server.py
```

## Out of Scope

- SQLite.
- Gmail write actions.
- Gmail email cache.
- Attachment indicators/opening (`PROD-05`, Phase 4).
- Grouping, severity, and operational dashboard features from Phase 4.

## Plan Verification

- Requirements covered: `ARCH-03`, `PROD-02`.
- Context decisions covered: `D-01` through `D-10`.
- New attachment requirement `PROD-05` deliberately excluded and routed to Phase 4.
