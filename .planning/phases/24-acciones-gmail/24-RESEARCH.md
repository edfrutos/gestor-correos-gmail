# Research: Phase 24 — Gmail Actions (Archive & Labeling)

## Context
Currently, the app can search (Readonly) and permanently delete (Full access) emails. Users need a "middle ground" action: Archiving (removing from INBOX) and applying custom Labels to organize treated emails without deleting them from Gmail.

## Goals
- Identify the Gmail API method for modifying labels (`users.messages.batchModify` or `users.messages.modify`).
- Determine the required OAuth scope. `https://www.googleapis.com/auth/gmail.modify` is perfect for this as it allows managing labels and archiving without full account deletion permissions.
- Design the UI for "Archive" and "Label" actions.

## Technical Analysis

### 1. Gmail API: `batchModify`
- Method: `POST https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/batchModify`
- Body: 
  ```json
  {
    "ids": ["id1", "id2"],
    "addLabelIds": ["LABEL_1"],
    "removeLabelIds": ["INBOX"]
  }
  ```
- This is efficient for bulk actions.

### 2. OAuth Scopes
- `gmail.readonly`: Current main scope.
- `gmail.modify`: Required for archiving and labeling.
- `https://mail.google.com/`: Current destructive scope (already has modify permissions).
- **Decision:** Use `gmail.modify` for these "soft" write actions. We might need a third token file (`modify_token.json`) or upgrade the main one? 
- **Better Decision:** Since the user already has a mechanism for "Destructive Authorization", we can add a "Gmail Management Authorization" (`gmail.modify`).

### 3. UI/UX Design
- **Archive Button:** A simple "Archivar" button in the blue bulk action bar.
- **Label Button:** A "Etiquetar" button that opens a simple list of existing user labels.
- **Feedback:** Update the UI state after archiving (e.g., mark as archived or remove from search results if the search was restricted to INBOX).

### 4. Integration with "Ocultar"
- `Ocultar` remains a local UI-only action.
- `Archivar` is a real action on Gmail.
- Often, a user will want to `Archive` AND `Hide` (Ocultar). We should consider if "Archivar" should automatically hide the message locally too.

## Strategy
1. **Scopes:** Add `gmail.modify` to the requested scopes when the user wants to perform these actions.
2. **Backend:** Implement `archive_messages(ids)` and `label_messages(ids, label_id)`.
3. **Frontend:** Add buttons to the bulk action bar.

## Verification Plan
- Archive a message and verify in Gmail Web that it's no longer in the Inbox.
- Apply a label and verify in Gmail Web.
- Verify that these actions can be performed on multiple messages.
