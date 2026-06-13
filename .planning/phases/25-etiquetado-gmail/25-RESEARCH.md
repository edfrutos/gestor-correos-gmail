# Research: Phase 25 — Gmail Label Management

## Context
After implementing Archiving (Phase 24), users need to organize emails by applying custom Gmail labels. This allows marking emails as "Processed", "Technical", or any other organization system they use in Gmail.

## Goals
- Identify the Gmail API method for listing user labels (`users.labels.list`).
- Identify the method for applying labels to multiple messages (`users.messages.batchModify`).
- Design a UI to select from existing labels.

## Technical Analysis

### 1. Gmail API: Listing Labels
- Method: `GET https://gmail.googleapis.com/gmail/v1/users/{userId}/labels`
- Filters: We should only show `user` type labels, excluding system labels like `CHAT`, `SENT`, `INBOX`, unless they are relevant.
- Formatting: Labels have an `id` and a `name`.

### 2. Gmail API: Applying Labels
- Method: `users.messages.batchModify` (same as Archiving).
- Body:
  ```json
  {
    "ids": ["id1", "id2"],
    "addLabelIds": ["LABEL_ID"],
    "removeLabelIds": []
  }
  ```

### 3. UI/UX Design
- **Trigger:** A "Etiquetar" button in the action bar.
- **Selection:** A simple modal that fetches the labels list when opened. 
- **Searchable List:** If the user has many labels, a search box inside the modal would be useful.
- **Combo Action:** Some users might want to "Label AND Archive". We can add a toggle in the label modal: "[x] Archivar al aplicar".

## Strategy
1. **Backend:** 
   - Add `get_labels()` to `gmail_client.py`.
   - Add `apply_label(ids, label_id, archive=False)` to `gmail_client.py`.
   - Update `server.py` with `/api/labels` and `/api/messages/label`.
2. **Frontend:**
   - Create a label selection modal in `index.html`.
   - Implement the fetching and applying logic in `static/app.js`.

## Verification Plan
- List labels and verify they match the user's Gmail account.
- Apply a label to 1 message and verify in Gmail Web.
- Apply a label to multiple messages and verify.
- Verify "Label + Archive" combined action.
