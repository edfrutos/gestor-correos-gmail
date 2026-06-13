# Research: Phase 21 — Search in Manage Hidden Modal

## Context
The "Manage Hidden" modal displays all emails that have been locally hidden. As the number of hidden emails grows (paginated in batches of 20), it becomes harder to find specific messages to restore or permanently delete.

## Goals
- Add a search input in the "Manage Hidden" modal.
- Allow filtering by Subject, Sender, or ID.
- Determine if search should be server-side or client-side.

## Technical Analysis

### Option A: Client-side Filter (Current Page only)
- Pros: Immediate, no new API calls.
- Cons: Only filters what's visible on the current page of 20 items. Not very useful for large collections.

### Option B: Server-side Search (Full Collection)
- Pros: Searches through all `hidden_ids` in `app_state.json`.
- Cons: Requires resolving metadata (Subject/From) for all matches. Resolving metadata from Gmail is slow if done for hundreds of IDs.

### Option C: Hybrid Search (Local Metadata Cache)
- The app doesn't persist Gmail content. It only has IDs. 
- **Compromise:** Search by ID is easy. Search by content requires the messages to be resolved.
- **Proposed Approach:** Add a `q` parameter to `/api/hidden`. The backend filters the list of IDs. However, since the backend doesn't store subjects, it can't filter by subject without fetching from Gmail.
- **Better Approach:** Keep the current pagination but add a search input that triggers a *client-side* filter *if* the user has loaded all pages? No.
- **Final Proposal:** Since we only store IDs, a true search by "subject" in the hidden modal requires resolving those IDs. 
- **Alternative:** Add a "Search" parameter that the backend uses to query Gmail *specifically* for IDs that are also in the `hidden_ids` list. 
  - Gmail Query: `from:sender subject:text`
  - Then intersect the results with `hidden_ids`.

## UI/UX Design
- Input field at the top of the modal (similar to the main toolbar).
- "Clear" button.
- Status indicator (e.g., "Found 5 matches in hidden list").

## Strategy
1. **Frontend:** Add the search input.
2. **Backend:** Update `/api/hidden` to accept an optional `q` parameter.
3. **Execution:** If `q` is present, the backend performs a Gmail search with that query, then filters the results to only include IDs that are in the local `hidden_ids` list.
4. **Benefit:** This allows searching by subject/sender using Gmail's own powerful search engine, but restricted to our hidden subset.

## Verification Plan
- Search for a specific sender in the hidden modal and verify only their hidden messages appear.
- Search for a word in the subject and verify matches.
- Verify that visible (non-hidden) messages do not appear in the search results of the hidden modal.
