# Phase 3 Research: Persistencia Local

## Research Goal

Determine the smallest reliable way to persist app state locally without caching Gmail content or expanding OAuth scopes.

## Current System

- `server.py` serves `index.html` and exposes `GET /api/status` and `GET /api/search`.
- `gmail_client.py` owns OAuth, Gmail status, message normalization, and sender search.
- `validators.py` contains API validation patterns through `ApiError`.
- `index.html` stores runtime state in memory:
  - `customSrcs`: user-added sender sources.
  - `deleted`: locally hidden email IDs.
  - `cf`, `cq`, `activeCat`: source/search/category preferences.
  - `selected` and `selMode`: transient selection state that should not persist.

## Recommended Approach

Use a project-local JSON state file with atomic writes and strict normalization.

Suggested file:

- `app_state.json`

Suggested schema:

```json
{
  "version": 1,
  "custom_sources": [
    {"dom": "web.dev", "label": "web.dev", "color": "#34d399"}
  ],
  "hidden_ids": ["19e77297ae301c51"],
  "preferences": {
    "source_filter": "all",
    "category_filter": "all",
    "search_query": ""
  }
}
```

## API Shape

Recommended endpoints:

- `GET /api/state`: returns normalized state, creating defaults in memory if no state file exists.
- `POST /api/state`: accepts the full normalized state and writes it atomically.

This is simpler than granular endpoints for the current single-user local app and avoids endpoint sprawl.

## Validation Rules

- Reject unknown or oversized payloads.
- Accept only `version`, `custom_sources`, `hidden_ids`, and `preferences`.
- Validate source domains using the same domain constraints as sender validation.
- Persist only user-added source metadata: domain, label, color.
- Persist hidden Gmail IDs as bounded strings; do not persist subject, snippet, body, sender, or other Gmail message content.
- Preferences should be whitelisted to known filter values and safe strings.

## UI Behavior

- Load `/api/state` before first render.
- Apply saved custom sources, hidden IDs, and preferences.
- Save after adding/removing sources, hiding/restoring emails, and changing preferences.
- Do not persist selection mode or selected email IDs.
- Provide a visible local recovery path for hidden emails, at minimum a counter plus "Restaurar ocultos" action.
- Saved sources may be displayed immediately after reload. If Gmail has an existing token, the UI may refresh saved sources from Gmail without opening OAuth; otherwise it should not trigger authorization automatically.

## Verification

Automated:

- Unit tests for storage defaults, normalization, validation, and atomic save/load.
- API tests for `GET /api/state`, `POST /api/state`, malformed JSON, invalid source domains, and absence of Gmail calls.
- Existing pytest suite remains green.

Manual:

- Add a custom sender, reload browser, source remains.
- Hide an email, reload browser and restart server, email stays hidden.
- Restore hidden emails, reload, emails reappear when present in current loaded email set.
- Change source/category/search filters, reload, preferences reapply.
- Confirm `app_state.json` contains no Gmail body/snippet/subject content.

## Risks

- Auto-refreshing saved sources on startup can unexpectedly open OAuth if token is absent. Guard this behind `/api/status.token === true`.
- Persisted hidden IDs for custom sender messages cannot be visibly restored until those messages are loaded again from Gmail, because Phase 3 deliberately avoids email caching.
- Overly permissive state payloads could accidentally store Gmail content. Use a whitelist schema.

## Research Complete

The phase can be planned as one vertical slice: local state module, API endpoints, frontend hydration/save, docs, and tests.
