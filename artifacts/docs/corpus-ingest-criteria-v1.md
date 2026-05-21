# Corpus ingest selection criteria — v1

**Status:** Approved for implementation (Phase 0)  
**Last updated:** 2026-05-20  
**Architecture summary:** [`system-design.md`](system-design.md) §12.1  
**Research input:** [`corpus-research-practitioner-compass.md`](corpus-research-practitioner-compass.md)  
**Execution plan:** Cursor plan `corpus_ingest_criteria_153b4093` (todo sequencing + Phase D doc checkpoints)

**TD-7 boundary:** This document governs **pre/post-Gemini selection only**. Gemini extraction prompts and HI-9 classification contract are unchanged.

---

## 1. Problem

Nightly batch ingest (`corpus_ingest.py`) discovers candidates via EnsembleData keyword/hashtag search, then sorts by **`play_count` DESC** and extracts the top ~30 videos/niche. `breakout_ratio` and `save_rate` are computed at row build but **never used for selection**. Post-extract quality issues log warnings only — rows still upsert.

**Product goal:** Fewer, more **instructive** extracts aligned with creator doomscroll jobs (Q1–Q3 in [`product-value-audit.md`](product-value-audit.md)) — relative breakout + replicable structure, not a view leaderboard.

**Ingest-worthy (Minh-tier):** A video earns Gemini extraction if a creator in the **micro–macro band** (1k–1M followers) in the same **content_class** would **save it as a reference** when researching “hôm nay quay gì?” — not because a mega-account repost hit 500k views.

---

## 2. Modes (`CORPUS_INGEST_MODE`)

| Mode | Behavior |
|------|----------|
| `legacy` | Current: flat view floor, sort by `play_count`, VPN=30 default |
| `shadow` | Compute purity stack + log deltas; **legacy selection still ships** |
| `purity` | Full Tier 0–2 stack + instructiveness rank; VPN default **15** |

Rollback: set `CORPUS_INGEST_MODE=legacy` on batch pod (no migration revert needed).

---

## 3. Criteria stack

### Tier 0 — Source hygiene (pre-pool)

- Keep: blocklist, VN gates, `BATCH_RECENCY_DAYS=30` discovery pool.
- **7d recency bonus** in Tier 2 rank; optional **`CORPUS_INGEST_MAX_AGE_DAYS=14`** hard gate in purity mode.
- **Diversity caps (pre-Gemini):** max **2** candidates per `creator_handle`/niche/night; max **2** per `sound_id`.

### Tier 1 — Hard reject (pre-Gemini)

Must pass **all**:

- Not blocklisted; VN creator/caption.
- **Tiered view floor** by `creator_tier`:

| `creator_tier` | Followers | Min views |
|----------------|-----------|-----------|
| nano | <1k | 3,000 |
| micro | 1k–10k | 5,000 |
| mid | 10k–100k | 15,000 |
| macro | 100k–1M | 25,000 |
| mega | ≥1M | 80,000 |

- ER ≥ `BATCH_MIN_ER` (default 2%) OR carousel likes ≥ `BATCH_CAROUSEL_MIN_LIKES`.
- **Instructiveness OR** — at least one of:
  - `breakout_ratio ≥ 2.0` (views / author median) when median present
  - R3 `breakout_proxy ≥ 2.0` when median missing
  - `velocity_score ≥ CORPUS_VELOCITY_GATE_MIN` (default 0.15)
  - `play_count ≥ REFERENCE_INGEST_MIN_VIEWS` (100k) **and** ER ≥ 3%
- **Boost-suspect:** shadow/log at flip; **hard reject `suspect_medium` only after Phase 5** (FP <15% on manual sample).

**Convergence gate (purity):** pass **≥3 of 4** batch proxies:

1. Breakout OR velocity (above)
2. Comment OR save depth (`comment_rate` ≥ niche p50 OR `save_rate` rank component in top half)
3. Format/sound signal (hashtag match OR `sound_momentum_bonus > 0` OR original sound)
4. Not `would_reject_boost_suspect` when hard reject enabled

### Tier 2 — Rank & cap (pre-Gemini)

**Canonical instructiveness score (0–100):**

```
instructiveness_score =
  25 * norm(breakout, cap=10)      # breakout_ratio or R3 proxy
+ Wv * norm(velocity_score)        # Wv=15 default; 25 when missing_median
+ 15 * norm(save_rate vs niche)
+ 12 * norm(comment_rate vs niche p50)
+ 12 * norm(ER)
+ 10 * recency_bonus(7d)           # 1.0 if ≤7d else decays
+  6 * sound_momentum_bonus         # §5
+  5 * niche_hashtag_match         # signal_hashtags hit
- R2 hook penalty                 # §4 R2, max 15
```

Sort DESC → take top **K** (`BATCH_VIDEOS_PER_NICHE`, purity default **15**). Apply creator/sound caps after sort.

**Save-rate soft floor:** only when niche has **≥100** corpus rows with `save_rate` populated **and** candidate `views ≥ niche_p75` → require ED `save_rate ≥ 1%`. Thin niches: rank only, no floor.

---

## 4. Risk mitigations

### R1 — Dynamic relaxing gate

**Trigger:** after Tier 1 scan, `tier1_pass_count ≤ CORPUS_RELAX_TRIGGER_MAX` (default **5**).

| Round | Action |
|-------|--------|
| R1a | Disable `CORPUS_INGEST_MAX_AGE_DAYS` for this niche only |
| R1b | Convergence **≥3/4 → ≥2/4** for this niche only |
| R2 | Lower tiered min views **−30%** (floor: nano 3k, micro 5k) |

**Minimum extract floor:** if still `< 3` passes after R2, allow top **3** by instructiveness with `ingest_relaxation_tier=2`.

Persist `ingest_relaxation_tier`: `0` strict | `1` recency/convergence | `2` view-floor.

**Replaces** volume-based `compute_thin_niche_multiplier` as default driver; purity allocator adds **+3 VPN** when shadow Tier 1 pass rate **>50%** for niche.

### R2 — Caption hook pre-filter

`predict_hook_from_caption(caption) → HookType | None` via VN regex markers (internal ingest only).

- If predicted type count **≥3** **and** breakout estimate **< 3.0**: `instructiveness_score -= CORPUS_HOOK_PREDICT_PENALTY` (default **15**).
- If count **≥5** **and** breakout **< 3.0**: skip pre-Gemini unless K unfilled.
- **Bypass:** no penalty/skip when breakout **≥ 3.0**.

### R3 — Internal niche proxy (missing author median)

Prefetch at batch start: `niche_id → { p50_views, p75_views }` from `video_corpus` (trailing 30d, `language='vi'`). Fallback: `organic_avg_views` when `sample_size ≥ 20`; else global p50.

```
breakout_proxy = views / max(niche_p50_views, 1)
```

When median missing: use proxy for Tier 1 OR-gate and breakout component; **velocity weight 15→25%**; log `breakout_source`: `author_median` | `niche_p50` | `niche_avg_fallback` | `none`.

Author handle cache per batch night; continue on proxy if `missing_median` rate **>30%** (no niche abort).

---

## 5. sound_momentum_bonus

Source: latest `trend_velocity.sound_trends` for `(niche_id, week_start)`.

| Bucket | Bonus (of 6 pts max) |
|--------|----------------------|
| `accelerating` | +6 |
| `peaking` | +3 |
| `cooling` | 0 |
| No match | 0 |

Optional: `CORPUS_SOUND_ORGANIC_BONUS=1` adds +1 within cap when `is_original_sound=true`.

---

## 6. Boost-suspect heuristic

Pre-Phase 5: percentiles from `niche_intelligence`; thin = `sample_size < 50` → **global** trailing-90d corpus percentiles (no `reference_eligible` filter).

**`suspect_medium` when:**

- (a) `views ≥ niche p90` **and** (b) `ER < niche p25` **or** `comments/views < niche p10`
- **Strong:** `comments == 0` AND `views ≥ max(10k, niche p75 views)`

Phase 1–2: log `would_reject_boost_suspect` only. Phase 5: hard reject + persist `boost_attribution`, `reference_eligible=false`.

---

## 7. Tier 3 — Post-extract reject

**3a (pre-2026-06-15) — hard failures only:**

- Non-VN caption (CJK >25% share — port of `nonVietnameseFilter.ts`)
- `content_format` null + `scene_count < 2` + no `hook_phrase`
- News/aggregator text markers
- Hook–content mismatch (hook topic keywords absent from transcript/topics/pain_points)

**3b (post-2026-06-15):**

- Hook-type cap: **>3** same normalized `hook_type`/niche/night **unless** `breakout_ratio ≥ 3.0` (or proxy)
- Re-check `suspect_medium` when Phase 5 live

Exempt: `ingest_source=user_diagnosis` promotion path.

---

## 8. Environment variables

| Variable | Default (purity) | Notes |
|----------|------------------|-------|
| `CORPUS_INGEST_MODE` | `legacy` → flip `shadow` then `purity` | |
| `BATCH_VIDEOS_PER_NICHE` | `15` (purity) / `30` (legacy) | |
| `KEYWORD_SEARCH_AUTHOR_STATS` | `true` on batch pod | ED cost trade |
| `CORPUS_INGEST_MAX_AGE_DAYS` | `14` (purity) / off (legacy) | Tier 1 optional |
| `CORPUS_RELAX_TRIGGER_MAX` | `5` | R1 trigger |
| `CORPUS_RELAX_VIEW_FLOOR_PCT` | `0.30` | R1 R2 round |
| `CORPUS_HOOK_PREDICT_PENALTY` | `15` | R2 |
| `CORPUS_VELOCITY_GATE_MIN` | `0.15` | Tier 1 OR |
| `CORPUS_SOUND_ORGANIC_BONUS` | `1` | sound tie-break |
| `CORPUS_INGEST_SHADOW_LOG` | `true` in shadow | structured logs |
| `CORPUS_BOOST_HARD_REJECT` | `false` until Phase 5 | |
| `ED_BATCH_COMMENT_FETCH_KILL_PCT` | `15` | Phase 5b kill-switch |
| `CORPUS_POSTEXTRACT_HOOK_CAP` | `3` | Phase 3b |
| `CORPUS_HOOK_CAP_BREAKOUT_BYPASS` | `3.0` | Phase 3b |

---

## 9. Shadow gate matrix (Phase 1 → Phase 2)

| Criterion | Safe threshold | If fail |
|-----------|----------------|---------|
| Thin-niche starvation | ≤2 niches at 0 extract after R1 (corpus_count <100) | Tune R1/R2 |
| Hook pre-filter precision | ≥80% on n=30 sample vs Gemini `hook_type` | Shrink markers |
| Author median error rate | <30% `missing_median`/night | R3 proxy |
| Proxy top-K “Minh save?” | ≥70% when >50% rows use non-median proxy | Adjust weights |
| Legacy reject rate | ≥25% stable 3 nights | Proceed |
| Boost-suspect FP | <15% on n=20 organic breakouts | Delays Phase 5 only |

---

## 10. Minh save rubric (shadow QA)

**Question:** “Minh cùng content_class có save video này làm reference sáng nay không?”

| Criterion | Pass if |
|-----------|---------|
| Peer breakout | breakout_ratio/proxy ≥2 OR clear velocity spike |
| Repeatable structure | Decodable hook/format (caption or post-extract) |
| Niche fit | VN + on-niche; not news aggregator |
| Not ads-skew | Would not flag `suspect_medium` under shadow rules |

**Pass row:** ≥3/4. **Niche pass:** ≥70% of n=20. Log in [`artifacts/qa-reports/corpus-ingest-criteria-baseline.json`](../qa-reports/corpus-ingest-criteria-baseline.json).

---

## 11. Launch kill gate (2026-06-15)

**Minimum shippable:** Phase 0+D0 → 1 (shadow) → 2+D1 (purity) → 3a → 4a.

Post-15/6 OK: Phase 5, 3b, 5b, 4b, D2.

---

## 12. Flip checklist (Phase 2 + D1)

- [ ] Shadow matrix green OR documented human exceptions
- [ ] `CORPUS_INGEST_MODE=purity` on batch pod
- [ ] `BATCH_VIDEOS_PER_NICHE=15`
- [ ] `KEYWORD_SEARCH_AUTHOR_STATS=true`
- [ ] `system-design.md` §12.1 live + changelog + `.env.example`
- [ ] Human sign-off on this doc (thresholds frozen unless amendment log)

---

## 13. Phase 5b enable gate

Enable top-10/niche ED comment fetch when **both**:

- Purity live **and**
- Shadow median shadow top-10 `breakout_ratio` **≥ +20%** vs legacy on **≥60%** niches (3-night avg), **OR** top-10 Jaccard **≤ 0.55** on **≥60%** niches.

---

## 14. Success metrics (14 nights post-flip)

| Metric | Target |
|--------|--------|
| Median `breakout_ratio` new rows | ↑ ≥30% vs legacy |
| Share `breakout_multiplier ≥ 2` | ↑ ≥20% |
| Gemini extract cost/night | ↓ ~40–50% |
| Shadow legacy reject rate | ≥25% × 3 nights |

---

## Appendix A — Shadow observation SQL (Phase 1)

Run nightly after `CORPUS_INGEST_MODE=shadow` on batch pod. Parse `[corpus_shadow]` JSON logs in Cloud Logging for top-10 deltas.

```sql
-- Median breakout_ratio of rows indexed last night vs trailing 7d baseline
SELECT niche_id,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY breakout_ratio) AS p50_breakout,
       count(*) AS n
FROM video_corpus
WHERE indexed_at >= now() - interval '1 day'
GROUP BY niche_id;

-- Niches with zero extracts (check batch summary niche_results)
-- Thin-niche starvation: count niches with corpus_count < 100 and 0 inserts in last run
```

---

## Amendment log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-20 | v1 initial spec from plan f76e0e39 + 153b4093 | Phase 0 |
| 2026-05-20 | Code landed: instructiveness modules, migration, consumers; default mode `legacy` | Implementation |
