# Repository Guidelines

> **Estado del proyecto (canónico):** [`.planning/STATE.md`](.planning/STATE.md).
> Roadmap: [`.planning/ROADMAP.md`](.planning/ROADMAP.md) · Requisitos: [`.planning/REQUIREMENTS.md`](.planning/REQUIREMENTS.md) · Decisiones: [`.planning/DECISIONS.md`](.planning/DECISIONS.md).
> No repitas cifras de estado (versión, nº de tests) en otros documentos: remite a `STATE.md`.

## Project Structure & Module Organization

This repository is a small local Gmail helper app. `server.py` is the Python entry point and serves both the API and a closed allowlist of static frontend assets. Readonly Gmail/OAuth logic lives in `gmail_client.py`, isolated permanent-delete authorization in `destructive_gmail.py`, parameter validation in `validators.py`, backend classification rules in `classifier.py`, local persistence in `storage.py`, and optional AI-provider access in `ai_client.py`. `index.html` contains the browser structure, while `static/app.css`, `static/app.js`, and `static/summary.js` contain styles and client-side behavior. `README.md` documents user setup. Do not add archived UI copies containing real Gmail data; Gmail remains the only source of message content.

## Build, Test, and Development Commands

Install runtime dependencies once:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the app locally:

```bash
.venv/bin/python server.py
```

The server listens on `http://localhost:8765`, serves `index.html`, exposes passive `/api/status`, and searches Gmail through `/api/search?sender=example.com&max=30`.

Run tests:

```bash
.venv/bin/python -m pytest
```

## Coding Style & Naming Conventions

Keep `server.py` compatible with Python 3 and the standard library `http.server` pattern already used here. Use short, focused helper functions for Gmail access, date normalization, tagging, and request handling. Constants such as `PORT`, `BASE_DIR`, `CREDS`, and `TOKEN` should remain uppercase. Preserve the existing Spanish UI/API messages unless a change requires coordinated copy updates in both Python and HTML.

For frontend changes, keep structure in `index.html`, styles in `static/app.css`, main UI behavior in `static/app.js`, and summaries/trends/AI behavior in `static/summary.js`. Match the current compact class naming style and avoid adding external build tooling unless the project is deliberately restructured.

Load order is `shared.js → app.js → summary.js` (classic scripts). Any state that must cross `app.js` ↔ `summary.js` goes on the `App` namespace defined in `static/shared.js` (`App.api`, `App.state.*`, `App.config.*`), not on a bare global — see ADR-011. No inline event handlers in `index.html`; wire listeners from `app.js`.

## Testing Guidelines

Automated tests use `pytest` under `tests/`. For changes, run:

```bash
.venv/bin/python -m pytest
```

For manual verification, run:

```bash
.venv/bin/python server.py
```

Then open `http://localhost:8765`, confirm `/api/status` reports the expected Gmail state, and test a sender search from the UI. If adding tests later, prefer `pytest` for Python helpers and name files `test_*.py`.

## Commit & Pull Request Guidelines

The repository uses concise, imperative commit messages such as `Add Gmail status handling` or `Update sender search UI`. Pull requests should describe the user-facing change, list manual verification steps, link any issue, and include screenshots for visible UI updates.

## Security & Configuration Tips

Do not commit real `credentials.json`, generated `token.json`, destructive `delete_token.json`, or local `app_state.json` files. Treat Gmail data as private: avoid logging message bodies, tokens, or full personal email addresses unless needed for local debugging.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
