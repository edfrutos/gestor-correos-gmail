# Research: Phase 27 — Intelligent Bulk Actions (Auto-Archive)

## Context
After implementing Auto-Labeling (Phase 26), users want to further automate their inbox by automatically archiving messages that match specific low-priority or repetitive rules.

## Goals
- Add `auto_archive` capability to custom rules.
- Automatically remove `INBOX` label in Gmail and add to `hidden_ids` locally when a match occurs.

## Technical Analysis

### 1. Rule Schema
Update `storage.py` to include:
- `auto_archive`: Boolean.

### 2. Execution Logic
In `server.py` (post-search):
- Identify messages matching rules with `auto_archive: true`.
- Collect these message IDs.
- Call `archive_messages(ids)` (which removes INBOX).
- Update local `app_state.json` by adding these IDs to `hidden_ids`.

### 3. UI/UX Design
In the Rule Modal:
- Add checkbox: `[ ] Archivar automáticamente (quita de Recibidos y oculta localmente)`.

### 4. Combined Action
Gmail's `batchModify` can add and remove labels in one go:
```json
{
  "ids": ["..."],
  "addLabelIds": ["USER_LABEL"],
  "removeLabelIds": ["INBOX"]
}
```
We should optimize the backend to perform a single `batchModify` per target configuration.

## Strategy
1. **Schema:** Add `auto_archive` to `storage.py`.
2. **UI:** Update `index.html` and `static/app.js`.
3. **Backend Logic:** Refactor the auto-labeling loop in `server.py` to also handle auto-archiving and local hiding.

## Verification Plan
- Create a rule with `auto_archive: true`.
- Perform a search that includes matching emails.
- Verify in Gmail web: message is labeled AND removed from Inbox.
- Verify in App: message is added to "Ocultos" automatically and not shown in the main results.
