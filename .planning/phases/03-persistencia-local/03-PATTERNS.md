# Phase 3 Pattern Map: Persistencia Local

## Closest Existing Patterns

### `server.py`

- Pattern: thin `BaseHTTPRequestHandler` methods delegate to helpers, then return JSON through `j()` or `err()`.
- Apply to Phase 3: add `do_POST`, route `/api/state`, and keep storage details outside `server.py`.

### `validators.py`

- Pattern: validation failures raise `ApiError(message, status, detail)`.
- Apply to Phase 3: state validation should raise `ApiError` and preserve Spanish API error copy.

### `tests/test_server_api.py`

- Pattern: `DummyHandler` exercises handler methods directly with `BytesIO`; monkeypatch isolates external dependencies.
- Apply to Phase 3: extend the dummy handler with request-body support for `POST /api/state` tests.

### `gmail_client.py`

- Pattern: module-level constants for local files (`CREDS`, `TOKEN`) and helpers for normalization.
- Apply to Phase 3: use a dedicated `storage.py` with `STATE_FILE`, `DEFAULT_STATE`, `load_state()`, `save_state()`, and `normalize_state()`.

### `index.html`

- Pattern: all state mutations currently call `renderSenders()`, `renderCats()`, and `render()`.
- Apply to Phase 3: call a debounced state save after the same mutations rather than scattering persistence logic through render-only code.

## Data Flow

1. Browser loads `/api/state`.
2. Browser applies persisted `custom_sources`, `hidden_ids`, and `preferences`.
3. Browser renders the current state.
4. User changes local state.
5. Browser posts normalized state to `/api/state`.
6. Python writes `app_state.json` atomically.

## Files to Modify

- `storage.py`: new state module.
- `server.py`: route and request-body handling.
- `index.html`: hydrate/save/restore local state.
- `.gitignore`: exclude `app_state.json`.
- `README.md`: document local state.
- `tests/test_storage.py`: storage tests.
- `tests/test_server_api.py`: endpoint tests.

## Constraints

- Do not move Gmail/OAuth code into storage.
- Do not persist Gmail snippets, bodies, subjects, or attachments.
- Do not trigger Gmail OAuth from `/api/state` or `/api/status`.
- Preserve existing Spanish UI/API messages.
