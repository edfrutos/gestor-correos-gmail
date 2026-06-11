# Phase 3: Persistencia Local - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 03-persistencia-local
**Areas discussed:** Storage format, Persisted state, Hidden email semantics

---

## Storage Format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON local | Sufficient for sources, hidden IDs, and preferences; simple, readable, and dependency-free. | ✓ |
| SQLite | More robust if the app needs history, richer queries, reports, or incident grouping. | |
| Agent decides | Let the agent pick the simplest option compatible with the roadmap. | |

**User's choice:** Approved the proposed default.
**Notes:** JSON local is the locked Phase 3 direction. SQLite is deferred.

---

## Persisted State

| Option | Description | Selected |
|--------|-------------|----------|
| Config without email cache | Save sources, hidden IDs, and preferences; locate emails through Gmail as needed. | ✓ |
| Include cache | Also save local metadata/snippets to reduce Gmail calls and speed reloads. | |
| Sources only | Minimal persistence for custom sender sources; hidden IDs and preferences later. | |

**User's choice:** Approved the proposed default.
**Notes:** Do not store Gmail snippets or message bodies in Phase 3.

---

## Hidden Email Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Local + restorable | Does not touch Gmail; hidden IDs persist and can be recovered/reset locally. | ✓ |
| Local irreversible | Does not touch Gmail; recovery requires editing/resetting the state file. | |
| Gmail action | Archive/delete/label in Gmail, requiring broader OAuth scopes. | |

**User's choice:** Approved the proposed default.
**Notes:** The existing readonly contract remains intact. "Borrar" means hide from local view.

---

## the agent's Discretion

- Exact JSON file path/name and schema.
- Exact API shape for state load/save, provided it is tested and documented.

## Deferred Ideas

- SQLite for future reporting/history needs.
- Gmail write actions with broader OAuth scopes.
- Full editable rule management if it expands beyond minimal persisted preferences.
