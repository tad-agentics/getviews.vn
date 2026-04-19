# B.3.1 audit — `/channel/analyze` + `channel_formulas`

**Date:** 2026-04-27  
**Scope:** Phase B plan §B.3.1 vs shipped backend (`channel_analyze.py`, migration, `GET /channel/analyze`).

## Verdict: **GREEN** (ship-ready with documented deltas)

| Plan item | Status | Notes |
|-----------|--------|--------|
| `channel_formulas` table + JSONB formula/lessons | **Met** | Composite PK `(handle, niche_id)` — **intentional correction** vs plan snippet (`handle`-only PK) so one row per kênh × ngách. |
| `CLAIM_TIERS["pattern_spread"]` (10) gate | **Met** | `CORPUS_GATE_MIN` imported from `claim_tiers.py`. |
| Thin response `formula: null`, `formula_gate: thin_corpus` | **Met** | No Gemini, no `decrement_credit`. |
| Cache TTL 7 days | **Met** | `CHANNEL_FORMULA_STALE_AFTER`, `_cache_fresh()`. |
| Credit only on Gemini path | **Met** | `decrement_credit` after cache miss + thick corpus. |
| `GET /channel/analyze?handle=` + auth | **Met** | `main.py`; 402 `insufficient_credits`, 404 niche/handle. |
| Gemini pydantic (formula ×4, lessons ×4, bio) | **Met** | `ChannelAnalyzeLLM`. |
| Service upsert | **Met** | `service_sb.table("channel_formulas").upsert(..., on_conflict="handle,niche_id")`. |
| `channel_corpus_stats` RPC | **Met** | Stable aggregate scan; `SECURITY INVOKER`; grants to `authenticated` + `service_role`. |
| RLS SELECT for authenticated | **Met** | No authenticated INSERT (writes via service_role only). |
| Tests (no network) | **Met** | `cloud-run/tests/test_channel_analyze.py`. |

## Should-fix / follow-ups (not blocking B.3.1)

1. **KPI richness** — ~~Plan KPI row 0 (MoM), row 3 (reach %) was stubbed in B.3.1~~ **Addressed in B.3.2** (posting cadence from `created_at`, MoM avg views, reach lift vs off-peak ER). See `channel_analyze.py` `LiveSignals` / `compute_live_signals`.
2. **Plan DDL typo** — Original plan `PRIMARY KEY (handle)` + `niche_id` column is inconsistent; shipped composite PK is the correct model.
3. **Bio source** — Plan TODO: `creator_velocity.bio` not in schema; B.3.1 uses Gemini one-liner cached in `channel_formulas.bio` (acceptable until ingest bio exists).

## Migration application

- **Remote:** Applied via Supabase MCP as migration name `b31_channel_formulas` (project `Getviews.vn`).
- **Local repo:** File `supabase/migrations/20260427100000_b31_channel_formulas.sql` remains canonical for `supabase db push` / branches.

## SQL verification (post-apply)

- `to_regclass('public.channel_formulas')` → `channel_formulas`
- `channel_corpus_stats` exists in `public`

---

## B.3.2 follow-up (same PR / session)

| Item | Status |
|------|--------|
| Posting cadence + peak time from `video_corpus.created_at` | **Shipped** — `compute_live_signals` → `_compute_posting_cadence_time_peak` |
| MoM avg views (30d vs prior 30d) | **Shipped** — `_compute_views_mom_delta` |
| Reach lift (peak-hour ER vs off-peak median) | **Shipped** — `_compute_reach_lift_delta` |
| Persist `posting_cadence` / `posting_time` on Gemini upsert | **Shipped** |
| Cache TTL (7d) unchanged; expose `computed_at` + `cache_hit` on JSON | **Shipped** |
| Live KPIs on cache hit (posting + MoM + reach refresh without Gemini) | **Shipped** |
