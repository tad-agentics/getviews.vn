# Platform width — Phase C.0.4

**Decision:** **Option A — 1280px canonical** (`phase-c-plan.md` default).

## Implementation

- CSS variable: `--gv-route-max-width: 1280px` in [`src/app.css`](../../src/app.css).
- Class `.gv-route-main` uses `max-width: var(--gv-route-max-width)` for all six routes (`/video`, `/kol`, `/channel`, `/script`, `/answer`, `/history`).
- Legacy `.gv-route-main--1280` kept as alias (same value) for gradual migration of TSX class names.

## Rationale

Aligns with shipped Phase B routes already using `gv-route-main--1280`; lowest QA risk vs lifting entire shell to 1380px.
