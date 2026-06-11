---
phase: 04
slug: inteligencia-operativa
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-01
---

# Phase 4 — UI Design Contract

> Visual and interaction contract for the operational panel. Generated from the existing dark compact UI language and the Phase 4 context decisions.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none |
| Icon library | Unicode glyphs and inline text symbols only |
| Font | `Syne` for titles and key labels, `DM Mono` for body, badges, and controls |

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | icon gaps, inline chip padding |
| sm | 8px | compact element spacing |
| md | 16px | control rows, card internal padding |
| lg | 24px | section padding and panel separation |
| xl | 32px | major layout gaps |
| 2xl | 48px | page-level separations |
| 3xl | 64px | top/bottom breathing room |

Exceptions: none.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Caption | 11px / `0.6875rem` | 500–700 | 1.35 |
| Secondary | 12px / `0.75rem` | 400–600 | 1.5 |
| Control | 13px / `0.8125rem` | 400–600 | 1.5 |
| Body | 14px / `0.875rem` | 400–600 | 1.55–1.75 |
| Subheading | 16px / `1rem` | 700 | 1.25 |
| Heading | 20px / `1.25rem` | 800 | 1.2 |

Notes:
- Use small positive letter spacing only for uppercase operational labels.
- Use fixed `rem` sizes; the mobile breakpoint may reduce only the main heading.
- Use `Syne` for headings only; use `DM Mono` for operational text, counts, timestamps, and button labels.
- Controls must remain at least `32px` high; search and sender inputs must remain at least `38px` high.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0d0f14` | page background |
| Secondary (30%) | `#13161e` / `#191d28` | panels, cards, modal surfaces |
| Accent (10%) | `#4a9eff` | active queue state, primary actions, focus, current export selection |
| Destructive | `#f87171` | local hide confirmation and destructive-style warnings |

Accent reserved for:
- active queue and view state
- primary action buttons
- focused input borders
- export mode selection
- Gmail link affordances

Secondary semantic colors may continue to distinguish categories/severity:
- green for low-risk or successful states
- purple for subscription/provider variation
- orange for billing or secondary export cues
- red for high severity and local hide confirmation

Avoid:
- beige/sand dominant palettes
- large gradients or decorative orbs
- more than one dominant accent family

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | `Exportar informe` |
| Empty state heading | `Sin acciones pendientes` |
| Empty state body | `La cola está vacía. Ajusta filtros o añade remitentes para localizar correos accionables.` |
| Error state | `No se pudieron cargar los correos. Reintenta la búsqueda o revisa la conexión con Gmail.` |
| Destructive confirmation | `Ocultar correo`: `Ocultar {n} correo(s) de la vista local. No afecta a Gmail.` |

Operational copy rules:
- Use Spanish in visible UI text.
- Be explicit when an action is local-only.
- Keep labels short: one verb + one noun where possible.
- Export scope must be chosen at the moment of export, not configured globally.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| none | none | not required |

---

## Phase-Specific Visual Contract

- The main experience is a single operational queue, not a marketing or dashboard hero.
- Provider grouping is primary, but the queue remains the top-level mental model.
- Use compact grouped sections or a toggle between queue and provider view only if it preserves the single prioritized queue as the default.
- Severity must be visible on each actionable item and should read before the subject/body snippet.
- Export controls belong in the action bar or a modal, not in a secondary settings screen.
- Markdown and JSON export must be treated as first-class equally valid formats.
- The export dialog must force the user to choose scope at export time.
- Attachment indicators remain accessible and should not steal visual priority from severity and queue order.
- Local hide remains labeled `Ocultar` and must continue to read as local-only.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** typography approved 2026-06-08; remaining dimensions retain their prior status.
