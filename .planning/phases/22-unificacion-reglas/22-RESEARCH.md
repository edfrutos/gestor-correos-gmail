# Research: Phase 22 — Rule Unification

## Context
Rules for classifying emails (categories, keywords, severity) are currently duplicated in:
- `classifier.py` (Python): Used for initial classification when fetching from Gmail.
- `static/app.js` (JavaScript): Used for UI display, filtering, and recalibrating categories if rules change locally.

## Duplicated Data
- `CATEGORIES` / `CATS`: Labels, emojis, and keyword lists.
- `CATEGORY_SEVERITY`: Map of category to base severity.
- `CATEGORY_SEVERITY_REASON`: Descriptions for why a severity was assigned.
- `SEVERITY_ORDER`: Priority of severities.

## UI Specific Data (currently in JS)
- Colors (e.g., `var(--d)`, `#f43f5e`).
- Emojis in labels (e.g., `💰 Monetario`).

## Proposed Strategy
1. **Source of Truth:** `classifier.py` will hold all data, including UI metadata.
2. **API Endpoint:** Add `GET /api/config` to `server.py`.
   - Returns categories, severity maps, and other constants.
3. **Frontend Update:**
   - On `init()`, fetch `/api/config`.
   - Populate `CATS`, `SEVERITY_META`, `CATEGORY_SEVERITY`, etc., from the API response.
   - Use these values for all local logic.

## Benefit
A single change in `classifier.py` (e.g., adding a keyword) will immediately reflect in both the backend classification and the frontend filters/UI.

## Technical Details
- `classifier.py` categories will be expanded to include `color` and `icon`.
- `server.py` will serve this as JSON.
- `app.js` will wait for this config before rendering or processing emails.

## Verification Plan
- Verify that category counts in the UI remain correct.
- Verify that filtering works as before.
- Add a new keyword in `classifier.py` and verify it appears in the frontend category description (if applicable) and affects filtering.
