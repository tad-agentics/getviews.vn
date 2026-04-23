# Corpus growth plan — 1,220 → 20K

**Date:** 2026-05-09
**Current state:** 1,220 videos across 21 niches. Max niche 128 (Review đồ ăn), median ~50, min 6 (Nhà cửa / Nội thất). Every niche is below the 500-video "exceptional" floor. **5 niches are under 35 videos — below the lifecycle/timing sample floor**, so users in those niches always see `MẪU MỎNG` fixture fallbacks.
**Target:** 20,000 videos rolling-30d (proxy for "comparable to a real data asset").
**Current daily rate:** ~100 videos/day (derived from 1,220 / 12 days). At this rate → 200 days to hit 20K.
**Acceptable rate:** 1,000-2,000 videos/day → 20K in 2-3 weeks.

---

## Pipeline knobs (all env-var tunable — no code deploy)

Defaults in `cloud-run/getviews_pipeline/corpus_ingest.py:52-73`:

| Var | Default | Effect |
|---|---|---|
| `BATCH_VIDEOS_PER_NICHE` | **10** | Videos ingested per niche per run |
| `BATCH_CAROUSELS_PER_NICHE` | 3 | Carousel posts per niche |
| `BATCH_KEYWORD_PAGES` | 2 | Keyword-search pages per niche |
| `BATCH_HASHTAG_FETCH_LIMIT` | 6 | Max signal_hashtags used per niche |

Theoretical throughput: 21 × (10 + 3) = **273 max posts per run**. Actual yield is lower due to dedup + quality gates.

---

## Levers ranked by leverage

### Lever 1 — Bump `BATCH_VIDEOS_PER_NICHE` 10 → 50 ★ highest leverage / lowest cost

- **Impact:** 5× growth per run. 273 → ~1,050 max posts/run.
- **Cost:** ~$2/run in Gemini Flash-Lite extraction ($0.002 × 1,050). EnsembleData units scale ~5×.
- **Implementation:** one env var on Cloud Run, no code deploy.
- **Risk:** ED daily budget cap (`ed_budget.py` has a daily ceiling — verify headroom before bumping).
- **Estimated outcome:** 1,220 → **5,000-7,000 in 7 days** if run daily.

```bash
gcloud run services update getviews-pipeline \
  --region asia-southeast1 \
  --update-env-vars BATCH_VIDEOS_PER_NICHE=50
```

### Lever 2 — Per-niche thin-niche prioritization

- **Problem:** Every niche currently gets the same quota regardless of size. Nhà cửa (6 videos) and Thú cưng (29 videos) deserve more than Review đồ ăn (128) per run.
- **Fix:** Pre-ingest query `niche_thinness = target - current_count`; give thin niches 2-3× the default quota; cap rich niches at 1×.
- **Impact:** Doesn't grow total much alone, but **shifts distribution toward coverage breadth** — more niches reach the 500 floor faster.
- **Implementation:** ~1 day in `_pick_hashtags_for_pool_fetch` + `run_batch_ingest`.
- **Dependency:** Lever 1 should ship first so there's quota headroom to shift.

### Lever 3 — Run ingest 2-4× daily

- Currently cron runs once/day at 20:00 UTC (runbook proposed).
- Bump to every 6 or 12 hours.
- **Impact:** 2-4× daily throughput. Paired with Lever 1 = 10-20× total.
- **Risk:** TikTok feeds have diminishing returns inside a short window — same videos re-fetched → dedup skips rise. Need to verify yield after the first 6h cycle before widening further.
- **Implementation:** Edit the cron.schedule() schedule string. Zero code changes.

### Lever 4 — Widen hashtag pool for undersized niches

Niches with suspiciously low hashtag counts today:

| Niche | Hashtags | Current videos |
|---|---|---|
| Tài chính / Đầu tư | 21 | 75 |
| Chị đẹp | 23 | 64 |
| Bất động sản | 24 | 49 |
| Nấu ăn / Công thức | 25 | 35 |

Compare to Travel (106 hashtags, 65 videos) — Travel is over-provisioned, Tài chính under.

- **Fix:** hand-curate or Gemini-generate ~50 more hashtags per undersized niche, UPDATE `niche_taxonomy`.
- **Impact:** Paired with Lever 1, un-bottlenecks the thin niches specifically.
- **Cost:** 1 Gemini call per niche, ~$0.01 total.

### Lever 5 — Add new niches (broaden taxonomy)

Current 21 niches, but real Vietnamese creator taxonomy is closer to 30-40. Candidates to add:

- Nội thất / Home design (currently only 6 rows in Nhà cửa — split further?)
- K-pop / Âm nhạc (separate from Chị đẹp which is VN-focused)
- Học tiếng (English/Chinese tutor content)
- Crypto / Web3
- Xe máy / Moto culture (separate from Ô tô)

- **Cost:** ~0.5 day per niche to define hashtag seed + validate classifier behaviour.
- **Impact:** +10-50 videos/niche/run on steady-state.

### Lever 6 — `deep_pool` flag for catch-up runs

Already built (`BatchIngestRequest.deep_pool=True`). Widens keyword_pages + videos_per_niche + carousels_per_niche by 2-3× for a single run. **Use case:** one-off catch-up or outage recovery, not steady-state growth.

- **Implementation:** Already available via `/admin/trigger/ingest` (just toggle the `deep_pool` checkbox in the admin UI).

---

## Recommended phased plan

### Phase 1 — this week (cheap, high-yield)

1. **Lever 1:** bump `BATCH_VIDEOS_PER_NICHE` → 50 via gcloud (1 command)
2. **Lever 4:** add ~50 hashtags each to Tài chính, Chị đẹp, Bất động sản, Nấu ăn (4 SQL UPDATEs)
3. Run `/admin/trigger/ingest` with `deep_pool=true` 2-3 times this week
4. Verify `batch_job_runs.summary->'total_inserted'` climbing (observability wired in PR #113)

**Expected outcome after 7 days:** 1,220 → **4,000-6,000**.

### Phase 2 — next week (code change)

5. **Lever 2:** implement thin-niche prioritization in `_pick_hashtags_for_pool_fetch`. Ship as a PR.
6. **Lever 3:** bump cron frequency to every 6 hours.

**Expected outcome after 14 days:** **12,000-18,000**.

### Phase 3 — week 3+ (taxonomy work)

7. **Lever 5:** add 5-10 new niches. Each needs hashtag seed + spot-check.

**Expected outcome after 21 days:** **20,000+** with broader coverage.

---

## Cost envelope at 20K

- **Gemini:** 20K videos × $0.003 avg = **$60 one-time** for extraction + analysis.
- **EnsembleData:** scales with pool_requests × unit_cost. Verify via `theoretical_ed_pool_requests()` in `ed_budget.py` before each phase.
- **Cloud Run compute:** negligible vs Gemini.

**Budget ceiling per CLAUDE.md is ~$70/mo all Gemini.** Phase 1 is safely inside. Phase 2+3 need a one-month budget bump to ~$100-120 until the 20K corpus stabilizes, then back to ~$20/mo for steady-state refresh + analytics.

---

## Starter actions (in order)

1. **Merge** `claude/runbook-apply-data-pipeline-crons` and **execute** it — no growth happens until the pipeline runs on schedule.
2. **Merge** `claude/admin-triggers-refresh-reclass-layer0` — unlocks manual triggers without curl.
3. **Bump Lever 1** (env var).
4. **Execute Lever 4** (hashtag SQL updates for 4 niches).
5. **Manually trigger** `/admin/trigger/ingest` with `deep_pool=true` once per day for 3-4 days.
6. **Then** commit to Phase 2 code work if Phase 1 yield meets expectations.
