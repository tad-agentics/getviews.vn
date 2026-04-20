# Phase D.0.6 — Spike close-out

**Date:** 2026-04-20
**Status:** Four deliverables merged; D.0.i pending production 7-day data pull (template ready).

---

## Deliverables

| # | Sub-task | Deliverable | Status |
|---|---|---|---|
| D.0.i | Measurement dashboard read (gating) | `artifacts/qa-reports/phase-d-d0-measurement-read.md` | ⏳ Template shipped; pending production 7-day data pull |
| D.0.ii | Gemini cost audit | `artifacts/plans/phase-d-gemini-cost-audit.md` | ✅ Call-site inventory locked; spend projection documented; tighten-or-leave decisions recorded |
| D.0.iii | Token dualism rebind map | `artifacts/plans/phase-d-token-rebind-map.md` | ✅ 39 files inventoried + clustered; rebind map + per-cluster grep commands locked |
| D.0.iv | PDF rendering stack decision | `artifacts/plans/phase-d-pdf-stack-decision.md` | ✅ WeasyPrint chosen; dep lines + Dockerfile patch drafted; fallback ladder preserved |
| D.0.v | Cross-pod SSE replay evaluation | `artifacts/plans/phase-d-sse-replay-decision.md` | ✅ No-op today; D.5.2 ships instrumentation first; Upstash escalation deferred until data exists |

---

## Locked decisions

### Migration sequencing

Latest on-main stamp: **`20260430000007`** (`usage_events_c1_answer.sql`
from C.1.4). D-era migrations bump from `20260430000008` or, for
simplicity + calendar alignment, from `20260501000000` (May 1 2026 UTC).

**Sequential stamps assigned:**

| Sub-phase | Filename | Stamp |
|---|---|---|
| D.1.1 `draft_scripts` — *already landed* in C.0 spike as `20260430000005_draft_scripts.sql` | (existing) | `20260430000005` |
| D.1.3 KOL `match_score` — *already landed* in C.0 spike as `20260430000006_creator_velocity_match_score.sql` | (existing) | `20260430000006` |
| D.2.3 `usage_events` D-set allow-list extension | `20260501000000_usage_events_d2.sql` | **`20260501000000`** |
| D.2.4 `/history` cross-type search GIN index | `20260501000001_history_search_gin.sql` | **`20260501000001`** |
| D.5.1 `gemini_calls` telemetry table | `20260501000002_gemini_calls.sql` | **`20260501000002`** |
| D.5.4 `chat_archival_audit` + archival job primitives | `20260501000003_chat_archival_audit.sql` | **`20260501000003`** |

If additional migrations surface during D, continue from
`20260501000004`+ in order. Never reuse a stamp; each migration must
land on both MCP remote + local file per `CLAUDE.md` Supabase rule.

### Token additions in `src/app.css`

**None expected in D.4.** D.4.1 swaps consumers; D.4.2 deletes the
legacy `--purple` / `--purple-light` / `--ink-soft` / `--border-active`
defs. If a `--gv-*` gap surfaces during D.4.1 (e.g. a legacy color
doesn't map cleanly to existing accent tokens), add the missing token
in the matching cluster commit with a one-line justification — not as a
separate commit.

### §J extension policy (restated)

Preserved from C.1.5 contract (`artifacts/docs/answer-session-contract.md`):

- **Additions only.** No field removals, no enum re-shapes, no `kind`
  discriminator changes during D.
- Server-side new fields use `Optional[...]` with a safe default;
  client-side new fields use `field?:` TypeScript optionals.
- UI renders humility / empty state when new optional fields are
  absent — never a silent hole.
- Pydantic invariants (`PatternPayload` `@model_validator` for
  WhatStalled, `Literal[...]` enums) stay intact.

D-era extensions expected (non-exhaustive, confirmed during
sub-phase kickoff):

- `ChannelAnalysisPayload.posting_heatmap: list[list[float]] | None`
  (D.1.4).
- `creator_velocity.match_score: int | None` +
  `match_score_computed_at: timestamp | None` (D.1.3 — already
  migrated, not yet wired).

---

## Pre-kickoff rules (restated for D.1 entry)

Carried from the Phase D plan §Pre-kickoff decisions:

1. **C ship-gate is the D ship-gate.** D.0.i blocks D.1+ deploys
   until the 7-day production data pull is green. No exceptions.
2. **`ReportV1` additions only.** Per above.
3. **D.4 is sequential, not big-bang.** 39 legacy-token consumers
   (D.0.iii); D.4.1 phases by cluster, D.4.2 deletes defs last,
   D.4.3 adds the lint guard.
4. **Cost surface is the call site.** D.5.1 dashboard groups by
   `metadata.call_site`, not `model_name`. D.0.ii locked the call-site
   inventory.
5. **Hard stop at Phase D — no new features.** Creator intents,
   commerce, Ship Next, loop closure, long-form strategy, and the
   three legacy-layout screen revamps all stay deferred indefinitely.
6. **D.4 legacy-layout purge is token-only.** Strict scope guard on
   `ExploreScreen.tsx`, `SettingsScreen.tsx`, `LandingPage.tsx` — 0
   JSX structure changes asserted against `git diff --stat`.

---

## Unblocked sub-phases

- **D.1** (Phase B carryovers) — unblocked for D.1.1 (pending D.0.i
  sign-off), D.1.2, D.1.3, D.1.4, D.1.5, D.1.6. D.1.1 depends on
  D.0.iv PDF stack decision (✅ WeasyPrint) + D.0.i measurement ship-gate.
- **D.2** (Phase C polish) — unblocked. D.2.3 extends allow-list per
  migration stamp above. D.2.5 tightens Pattern narrative per D.0.ii
  tighten decision.
- **D.3** (End-to-end review & closure) — unblocked. Runs after D.1
  + D.2 land so it audits what actually shipped.
- **D.4** (Token namespace deprecation + legacy-layout screen purge)
  — unblocked per D.0.iii rebind map. Runs after D.1 to minimise
  merge churn.
- **D.5** (Observability + cost) — unblocked. D.5.1 instrumentation
  specced per D.0.ii; D.5.2 instrumentation contract specced per
  D.0.v.

---

## Outstanding items (non-blocking)

1. **D.0.i production data pull.** Template + SQL + pass/fail contract
   shipped. Requires a human with production Supabase access to run
   the query + populate the 14-row table + append sign-off. Blocks
   D.1+ deploys (not D.1 kickoff / code writing).
2. **D.0.ii spend projection vs. actuals.** Call-site inventory is
   locked; actual token-spend numbers fill in when D.5.1 lands its
   dashboard (post-D.1). Cost ceiling ($70/mo per `CLAUDE.md`)
   re-verified during D.5.1 close-out.

---

## Sign-off

Four of five D.0 sub-tasks locked. D.0.i template + SQL + contract
shipped, awaiting production data pull. D.0.6 close-out complete —
all downstream sub-phases unblocked for kickoff, subject to the
D.0.i production gate before any D behavior change goes live.

**D.0 spike closure-complete pending D.0.i sign-off.**
