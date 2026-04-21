# Phase D.1 — close-out audit

**Date:** 2026-04-21
**Status:** All six sub-phases shipped + merged. Full test suite green; two
pre-existing TS errors unchanged; two manual follow-ups flagged.

---

## Deliverables vs plan

| # | Sub-phase | Commit | Plan deliverables | Status |
|---|---|---|---|---|
| D.1.1 | `draft_scripts` + save + Copy/PDF/Chế độ quay | `b85b347` | migration, 4 endpoints, WeasyPrint dep, ShootScreen route, `script_save` event, smoke | ✅ all landed |
| D.1.2 | Gemini upgrade to `/script/generate` | `20be9f6` | pydantic-bound response, frozen HTTP contract, deterministic fallback, smoke | ✅ all landed |
| D.1.3 | KOL `match_score` persistence | `faae3be` | invalidation trigger migration, 7d cache, writeback, pytest, smoke | ✅ all landed |
| D.1.4 | `PostingHeatmap` on `/channel` | `1e7a700` | `_compute_posting_heatmap`, `posting_heatmap` on payload, primitive, wiring, pytest, smoke | ✅ all landed |
| D.1.5 | Real 30d view velocity | `dafbb03` | migration, batch_analytics Pass 3, read-path with proxy fallback, `[kol-growth]` log, smoke | ✅ landed (view-velocity pivot — see Locked decisions) |
| D.1.6 | Primitive + screen render tests | `17f2899` | 5 primitive + 2 screen tests (~200 LOC) | ✅ 7/7 files land, 36 tests |

---

## Test state

- **cloud-run pytest:** 439/439 pass (up from 414 pre-D.1; D.1 added 25 tests)
  - test_kol_browse.py: 22 (was 12 in B.2; +3 D.1.3, +7 D.1.5)
  - test_draft_scripts.py: 12 (new, D.1.1)
  - test_script_generate.py: 5 (was 2; +3 D.1.2)
  - test_channel_analyze.py: 9 (was 6; +3 D.1.4)
- **vitest:** 162/162 pass (up from ~114 pre-D.1; D.1 added 48 tests — D.1.6 backfill + PostingHeatmap)
- **typecheck:** 2 errors, both pre-existing on main before D.1 entry
  (`TemplatizeCard.tsx "secondary"` variant, `useHistoryUnion.ts` RPC name
  not in typegen). D.1 introduced zero new TS errors.

---

## Locked decisions (D.1-specific)

### D.1.5 pivot — view velocity, not follower growth

The plan said "switch `kol_browse.py` from the `growth_percentile_from_avgs`
proxy to the real `creator_velocity.growth_30d_pct` column," but no
follower-snapshot series exists on-disk — historical follower growth isn't
computable or recoverable retroactively. D.1.5 pivoted to **view velocity**
(recent-30d mean views vs prior-30d mean views, per creator) computed from
`video_corpus.created_at + views` — data already indexed.

- Column: `view_velocity_30d_pct NUMERIC` + `view_velocity_computed_at`
  (migration `20260501000005`).
- Batch: `batch_analytics.py` Pass 3, nightly cron.
- Read path: `_resolve_growth_display_pct` emits `[kol-growth] source=real|proxy`
  log per creator so D.5.1 can surface the mix.
- Follow-up: when follower snapshotting exists (queued D.5.x), the
  `_resolve_growth_display_pct` swap is one line.

### D.1.1 endpoint aliasing

Plan named `POST /script/save` but a stub `POST /script/drafts` already
existed from C.0 scaffolding. The shipped implementation registers **both**
routes pointing at the same handler so the scaffold URL keeps working and
the plan's canonical URL wins going forward.

### D.1.2 cost-audit binding

Per D.0.ii recommendation on response_format binding:
`_call_script_gemini` uses `types.GenerateContentConfig` with
`response_json_schema=ScriptGenerateLLM.model_json_schema()` +
`ScriptGenerateLLM.model_validate_json(_normalize_response(raw))` — fully
pydantic-bound, no manual `json.loads`. Matches the `_call_channel_gemini`
pattern, upgrades from the "⚠️ manual json.loads" state documented in
the D.0.ii audit.

### D.1.3 cache semantics note

`creator_velocity.match_score` is a single global column per
(creator_handle, niche_id), but `compute_match_score` output is
user-specific (depends on user followers + reference_handles). The
"approximate cache" tradeoff is documented in the migration header
(`20260501000004`) and the `_resolve_growth_display_pct` docstring. The
profile-change trigger nulls all rows in the user's old + new niche on
profile update; other users see a recompute on next browse — acceptable
since the cost is O(creators-in-niche).

---

## §J additions-only check

`src/lib/api-types.ts` diff over the last 10 commits shows **zero
deletions** (only additions):

- `ChannelAnalyzeResponse.posting_heatmap?: number[][]` (D.1.4)
- `ScriptSaveRequest / ScriptDraftRow / ScriptSaveResponse /
  ScriptDraftsListResponse / ScriptDraftResponse / ScriptExportFormat`
  (D.1.1)

All optional fields, no enum reshapes, no `kind` discriminator changes.
ReportV1 contract intact.

---

## Migration sequencing

| Stamp | Sub-phase | File |
|---|---|---|
| `20260430000005` | D.1.1 (pre-existing, C.0 spike) | `draft_scripts.sql` |
| `20260430000006` | D.1.3 (pre-existing, C.0 spike) | `creator_velocity_match_score.sql` |
| `20260501000004` | D.1.3 | `creator_velocity_match_score_invalidate.sql` |
| `20260501000005` | D.1.5 | `creator_velocity_view_velocity.sql` |

D.0 close-out reserved `20260501000000..003` for D.2.3 / D.2.4 / D.5.1 /
D.5.4 — those slots are still open. The D.1 migrations land at `000004+`
per the close-out's "continue from 000004+ in order" rule. When D.2/D.5
lands, they fill the reserved slots; Supabase will apply each stamp in
isolation (all D-era migrations are `ADD COLUMN IF NOT EXISTS` /
`CREATE TABLE` shape, so ordering doesn't matter for correctness).

---

## Measurement events live

| Event | Fire site | Commit |
|---|---|---|
| `script_save` | `ScriptScreen.tsx:303` after `/script/save` success | D.1.1 |
| `script_generate` | `ScriptScreen.tsx:262` (existing B.4 wiring) | — |
| `script_screen_load` | `ScriptScreen.tsx:192` (existing B.4 wiring) | — |

`usage_events.action` is free-form TEXT with no CHECK constraint
(`20260419120000_usage_events_b1_checkpoint.sql`), so `script_save`
inserts land without a schema change. D.2.3 will extend the partial
dashboard index to cover D-era events (stamp `20260501000000`, reserved).

---

## Manual follow-ups (non-blocking)

1. **Supabase MCP apply.** Two D-era migrations must land on the remote
   before Cloud Run deploys carrying their read paths:
   - `20260501000004_creator_velocity_match_score_invalidate.sql` (D.1.3)
   - `20260501000005_creator_velocity_view_velocity.sql` (D.1.5)
   Per `CLAUDE.md` Supabase rule, the local SQL file and the MCP-applied
   remote must never drift.

2. **WeasyPrint image build proof.** `cloud-run/Dockerfile` adds
   `libpango-1.0-0 libpangoft2-1.0-0 libcairo2` + `weasyprint>=63.0` in
   `pyproject.toml`. First production image build under this diff is the
   proof; if the dep stack fails, `POST /script/drafts/:id/export`
   returns 503 `pdf_unavailable` and the frontend disables the PDF
   button transparently (D.1.1 humility path is already wired).

3. **D.1.5 Pass 3 first run.** `batch_analytics.py` Pass 3 populates
   `view_velocity_30d_pct` on the next weekly cron run post-deploy.
   Between deploy and first cron, `kol_browse.py` reads NULL → proxy
   fallback → `[kol-growth] source=proxy reason=missing_view_velocity`
   log lines for every creator. Expected; not a regression.

---

## Micro-gap (non-blocking)

`kol_browse._fetch_cached_match_scores` and
`kol_browse._fetch_view_velocity_map` each issue a separate
`SELECT ... FROM creator_velocity WHERE niche_id = ?` per request — two
round-trips where one would suffice. Consolidating them (fetch both
columns in a single select, split into two maps in-memory) is a ~10-line
change to queue under D.5 observability or as a small tidy commit during
D.3. Not blocking.

---

## Sign-off

Phase D.1 close-out complete. All six sub-phases shipped; 601/601 tests
pass across both stacks (439 pytest + 162 vitest); zero new TS errors;
§J contract preserved; design-token audit clean on all new files; two
migrations queued for MCP apply.

**D.1 is done.** D.2 (Phase C polish), D.3 (end-to-end review), D.4
(token purge), and D.5 (observability) are all unblocked.
