# Research: Phase 29 — Persistent Exports & Integrated Reader

## Context
The user wants to move away from browser-based downloads to a managed `exports/` folder within the app. Additionally, they require a built-in EML viewer to avoid opening external mail clients like Apple Mail.

## Goals
- Create and manage an `exports/` directory.
- Implement a backend parser for `.eml` files using Python's `email` module.
- Build a frontend UI for reading emails (headers, body, attachments).
- Support opening external `.eml` files via command-line arguments (for macOS Services integration).

## Technical Analysis

### 1. Persistent Exports
- Folder: `exports/` (ignored in `.gitignore`).
- Logic: When exporting, write to `exports/{filename}` and return the local path or a status.
- UI: A new "Bandeja de Exportaciones" to see and open these files.

### 2. EML Parser (Backend)
- Endpoint: `GET /api/view-eml?path=...` or `POST /api/view-eml` (sending content).
- Parsing: Use `email.message_from_bytes`.
- Sanitization: Strip `<script>` and suspicious tags from HTML bodies before sending to frontend.
- Attachments: List them and allow extraction.

### 3. Integrated Viewer (Frontend)
- A new modal or full-screen overlay `reader-modal`.
- Sections: Header (From, To, Date, Subject), Body (Tabbed text/html), Attachments list.

### 4. macOS Services / CLI Integration
- Support: `python server.py --view "/path/to/mail.eml"`.
- Action:
  1. Check if server is running.
  2. If yes: Send command to existing server (via a trigger file or internal API).
  3. If no: Start server and open browser at `http://localhost:8765?view=PATH`.
- Frontend: Detect `view` query parameter and auto-open the reader.

## Verification Plan
- Export an email and verify it exists in `exports/`.
- Open the built-in reader and verify it displays the content correctly without opening Apple Mail.
- Call the script from terminal with a path and verify it opens the viewer.
