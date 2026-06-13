# Research: Phase 28 — Optional AI Rule Suggestions

## Context
Users manually create rules or hide emails. The AI can help identify patterns (e.g., "You hide 90% of emails from notice@provider.com") and suggest a rule to automate this.

## Goals
- Detect recurring patterns in hidden/deleted emails.
- Generate rule suggestions via AI (optional).
- Add a UI toggle to enable/disable this feature.

## Technical Analysis

### 1. Pattern Detection
- Source of data: `hidden_ids` and current session activity.
- The app knows which senders/keywords are frequently involved in "Hide" or "Delete" actions.
- **Candidate extraction:** Aggregate hidden emails by domain/sender. If a sender has > X hidden messages and 0 rules, they are a candidate.

### 2. AI Prompting
- Input: List of candidates (Sender, common subject fragments).
- Request: "Generate a classification rule for this sender. Suggest a category (money, warn, etc.) and a severity."

### 3. Optionality (User Requirement)
- Add `ENABLE_AI_SUGGESTIONS` variable (environment and `app_state.json` preference).
- UI: A toggle switch in the "Custom Rules" header or a new "Settings" panel.

### 4. Suggestion Workflow
- If enabled: The app periodically (or on demand) shows a list of suggested rules.
- "Apply" button: Fills the Rule form with the suggestion.

## Strategy
1. **State:** Add `ai_suggestions_enabled` to `preferences` in `storage.py`.
2. **Backend:** 
   - Add endpoint `GET /api/ai/suggest-rules`.
   - Logic: Count domains in `hidden_ids` (requires resolving metadata, which is expensive).
   - *Better logic:* Use the currently loaded `activeEmails` that are marked as `deleted` (hidden) in the session.
3. **Frontend:**
   - Add toggle in the Rules panel.
   - Add "Sugerencias de la IA" section below the form.

## Verification Plan
- Enable suggestions and verify the section appears.
- Disable and verify it disappears.
- Hide several emails from a new sender and check if a suggestion appears.
