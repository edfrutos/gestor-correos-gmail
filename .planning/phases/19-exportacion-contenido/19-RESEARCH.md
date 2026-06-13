# Research: Phase 19 — Full Message Content Export

## Context
Phase 19 aims to allow users to export the full content (body) of selected emails. Currently, the application only handles headers, snippets, and attachments.

## Goals
- Identify the Gmail API method for retrieving full message content (including HTML/Plain text bodies).
- Determine the best format for exporting (EML vs. PDF vs. JSON/Markdown).
- Evaluate how to handle multiple exports (ZIP vs. concatenated file).
- Verify how to stream or bundle these exports without exceeding memory or timeout limits.

## Gmail API Investigation
- Method: `users.messages.get` with `format=raw` (for EML) or `format=full` (for parsed JSON).
- Permissions: `gmail.readonly` (already held) is sufficient for reading full content.

## Export Formats
- **EML:** Standard format, easily openable in mail clients. `format=raw` provides this directly from Gmail.
- **PDF:** Requires additional libraries (e.g., `weasyprint`, `pdfkit`), might be heavy for a simple tool.
- **Markdown/JSON:** Useful for data analysis but loses original formatting/attachments.

## Technical Strategy
1. **Backend:**
   - Add `/api/messages/export` endpoint.
   - Fetch `raw` content from Gmail for each ID.
   - If multiple IDs, bundle into a ZIP or return a multipart response? (ZIP is more standard for browser downloads).
2. **Frontend:**
   - Add "Export Full Content" button to the selection bar.
   - Show progress if exporting multiple messages.
   - Trigger download of the resulting file.

## Verification Plan
- Export a single email as EML.
- Export multiple emails as a ZIP of EMLs.
- Verify that no email content is saved to `app_state.json`.
