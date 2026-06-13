# Research: Phase 23 — Date-based Search & Literal Refinement

## Context
The user wants to filter messages by date ranges in the main window. If the text search is empty, the app should allow a "general context" search based only on dates.

## Goals
- Add date pickers (Start/End) to the UI.
- Support `after:` and `before:` Gmail operators.
- Make `sender` optional if dates are present.
- Improve literal search by allowing it to be passed to the backend (Gmail search).

## Technical Implementation

### 1. Gmail API Queries
- `after:YYYY/MM/DD`
- `before:YYYY/MM/DD`
- Combination: `from:example.com after:2026/01/01 before:2026/01/31 "text search"`

### 2. Backend Search Pipeline
- Current: `search(sender, max_r, custom_rules)`
- Proposed: `search(sender=None, after=None, before=None, q=None, max_r=30, custom_rules=None)`
- If `sender` is provided: query starts with `from:{sender}`.
- If `after`/`before` provided: append to query.
- If `q` (literal) provided: append to query.

### 3. UI/UX Changes
- Toolbar update: Add two `<input type="date">` fields.
- "Clear dates" button.
- The main "Search in Gmail" button should use all these parameters.

### 4. Search Behavior
- "Contexto general": If the user types nothing in the sender/literal boxes but selects a date range, the app searches Gmail for *everything* in that range (up to `max_r`).
- "Afianzando literal": The text search box in the toolbar could double as a Gmail query filter.

## Challenges
- Gmail API `threads().list` results might include messages outside the date range if only one message in the thread matches. We already filter by sender inside the thread; we might need to filter by date too.
- Validation: Ensure date formats are correct for Gmail (YYYY/MM/DD).

## Strategy
1. **Validators:** Relax `validate_sender` to allow empty values. Add `validate_date`.
2. **Gmail Client:** Update `search` to build a complex query string.
3. **Server:** Update `handle_search` to parse `after`, `before`, and `q`.
4. **Frontend:** Add the date pickers to the "Remitentes" panel or the main Toolbar.

## Verification Plan
- Search for emails from a specific sender within a 1-week range.
- Search for *any* email (no sender) within a 1-day range.
- Verify that the results respect the "literal" text if provided.
