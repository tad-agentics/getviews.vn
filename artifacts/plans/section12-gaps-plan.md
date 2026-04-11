# §12 Intelligence Layer — Gap Fix Plan

**Date:** 2026-04-08  
**Based on:** §12 compliance audit against Northstar v1.3  
**Scope:** 5 confirmed gaps across backend + infra

---

## Corrected audit (post-investigation)

Two items from the initial audit were already built:
- **PayOS** — `create-payment` + `payos-webhook` Edge Functions fully implemented. `PricingScreen` calls them. ✅
- **`daily_free_query_count` abuse protection** — column exists in `profiles` migration, reset cron exists. The **only gap** is that `main.py` doesn't increment or check it for free intents. (See Fix 4.)

Remaining gaps — 5 items in priority order:

---

## Fix 1 — `trend_velocity` computation (Layer 3)

**Priority: CRITICAL**  
**Why:** This is the central intelligence claim of §12. Trend Spike (⑥) and Content Directions (②) synthesize against it. Currently only seed data from April 2026 exists — no live computed shifts. Every user of these intents is getting stale, fictional data.

**What's missing:**  
No Python function populates `trend_velocity` with real week-over-week hook shift data from `video_corpus`.

**Files to create/modify:**
- **CREATE** `cloud-run/getviews_pipeline/trend_velocity.py` — new module
- **MODIFY** `cloud-run/getviews_pipeline/corpus_ingest.py` — call `run_trend_velocity()` in the Sunday weekly job alongside `batch_analytics` and `signal_classifier`

**Logic for `trend_velocity.py`:**

```python
# run_trend_velocity(client) → upserts trend_velocity rows

# Step 1: For each niche, query video_corpus for last 14 days
# Step 2: Group videos by hook_type, by week (this_week = last 7 days, prev_week = 7-14 days)
# Step 3: Compute per hook_type:
#   - this_week_count, prev_week_count → percentage shift
#   - this_week_avg_er, prev_week_avg_er → engagement shift
# Step 4: Build hook_type_shifts JSON:
#   { hook_type: { count_delta_pct, er_delta_pct, signal } }
# Step 5: Build new_hashtags from analysis_json.trending_hashtags (if present)
# Step 6: Upsert trend_velocity (niche_id, week_start, hook_type_shifts, format_changes, new_hashtags, sound_trends)

# Output schema matches migration:
#   hook_type_shifts JSONB
#   format_changes JSONB
#   new_hashtags TEXT[]
#   sound_trends JSONB
```

**Inject into synthesis (already wired but drawing on seed data):**  
`corpus_context.py` → `get_trend_velocity_for_niche()` already exists and reads from `trend_velocity`. Once the table is live-populated, all ② and ⑥ responses automatically improve.

**Effort:** ~4 hours. Self-contained module, no schema changes.

---

## Fix 2 — `min-instances: 1` in deploy.sh

**Priority: HIGH**  
**Why:** §13 explicitly mandates `min-instances: 1` for the user-facing Cloud Run service. With `min-instances: 0`, every first query of the day incurs a 5–15s cold start, added on top of the 20–30s pipeline time. This is a user-visible regression.

**File to modify:**
- `cloud-run/deploy.sh` — line 23

**Change:**
```bash
# Before
--min-instances 0 \

# After
--min-instances 1 \
```

**Cost impact:** +~$10–15/mo (one warm instance in Singapore at 1 CPU / 1Gi). Worth it.

**Effort:** 1 minute. Requires a `deploy.sh` run to apply.

---

## Fix 3 — Gemini retry / exponential backoff

**Priority: HIGH**  
**Why:** §13 mandates "3 retries, 1s/2s/4s delay" on Gemini 503/429. Currently `_generate_content_models` tries each model in the fallback chain once and gives up. A single transient Gemini error kills the user's query (or kills a batch niche run).

**Files to modify:**
- `cloud-run/getviews_pipeline/gemini.py` — `_generate_content_models()`

**Change — add retry loop inside the per-model attempt:**
```python
import time

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds

def _generate_content_models(...):
    client = _get_client()
    chain = [primary_model, *fallbacks]
    seen: set[str] = set()
    last_err: Exception | None = None
    for m in chain:
        if not m or m in seen:
            continue
        seen.add(m)
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                kwargs = {"model": m, "contents": contents}
                if config is not None:
                    kwargs["config"] = config
                return client.models.generate_content(**kwargs)
            except Exception as e:
                is_transient = _is_transient_gemini_error(e)
                if not is_transient or attempt == len(RETRY_DELAYS) - 1:
                    last_err = e
                    logger.warning("Gemini model %s attempt %d failed: %s", m, attempt + 1, e)
                    break
                logger.info("Gemini model %s transient error, retrying in %ds: %s", m, delay, e)
                time.sleep(delay)
    if last_err:
        raise last_err
    raise RuntimeError("No Gemini models available")

def _is_transient_gemini_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "503" in msg or "429" in msg or "rate limit" in msg or "quota" in msg or "overloaded" in msg
```

**Batch job behavior:** corpus_ingest already logs + skips individual video failures — the retry in gemini.py reduces the skip rate.

**Effort:** ~1 hour.

---

## Fix 4 — `daily_free_query_count` abuse gate for free intents

**Priority: MEDIUM**  
**Why:** §13 mandates checking a 100-query/day threshold for ⑥ Trend Spike and ⑦ Find Creators before processing. The column and reset cron exist but `main.py` never reads or increments it. A bot can call `/stream` with `trend_spike` unlimited times at $0.005/call.

**Files to modify:**
- `cloud-run/main.py` — `event_generator()`, after credit gate and before pipeline dispatch

**Change — add free-intent abuse check:**
```python
FREE_DAILY_LIMIT = 100

# After the credit gate, before pipeline dispatch:
if normalized in ("trend_spike", "find_creators", "follow_up"):
    # Increment and check daily free query count
    try:
        result = sb.rpc("increment_free_query_count", {"p_user_id": user_id}).execute()
        new_count = (result.data or {}).get("new_count", 0)
        if new_count > FREE_DAILY_LIMIT:
            yield _sse_line({"type": "error", "error": "daily_free_limit"})
            return
    except Exception as exc:
        logger.warning("[stream] free query count check failed: %s", exc)
        # Fail open — don't block user on counter error
```

**New Supabase RPC needed:**
```sql
-- New migration: increment_free_query_count
CREATE OR REPLACE FUNCTION increment_free_query_count(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_count INTEGER;
BEGIN
  UPDATE profiles
  SET daily_free_query_count = daily_free_query_count + 1
  WHERE id = p_user_id
  RETURNING daily_free_query_count INTO v_count;
  RETURN jsonb_build_object('new_count', v_count);
END;
$$;
REVOKE ALL ON FUNCTION increment_free_query_count(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION increment_free_query_count(UUID) TO authenticated;
```

**Frontend:** Add handler for `"daily_free_limit"` error code in `useChatStream.ts` — show a toast "Bạn đã dùng quá 100 lượt tìm kiếm hôm nay".

**Effort:** ~2 hours (migration + main.py + frontend error handler).

---

## Fix 5 — R2 permanent video URL for Explore playback

**Priority: LOW (deferred)**  
**Why:** `video_url` stored in `video_corpus` is an ephemeral ED CDN URL. §12 promises `videos/{video_id}.mp4` in R2 for zero-egress inline playback in Explore. ED CDN URLs typically expire in hours–days. Once the corpus grows, older videos in Explore will 404.

**What's needed:**
1. After downloading the clip in `corpus_ingest.py` (step 3), upload the full 720p/30s `.mp4` to R2 at `videos/{video_id}.mp4`
2. Store the R2 public URL as `video_url` instead of the ED CDN URL
3. `r2.py` needs an `upload_video(video_id, clip_path) → str` function

**Why deferred:** R2 isn't configured in production yet (only frames bucket). This requires provisioning a second R2 bucket or path, configuring `R2_BUCKET_NAME` for video, and updating the deploy env vars. Low urgency while corpus is small and ED URLs are still fresh. **Revisit at Month 2 when Explore playback reliability becomes user-visible.**

**Files:**
- `cloud-run/getviews_pipeline/r2.py` — add `upload_video(video_id, clip_path)`
- `cloud-run/getviews_pipeline/corpus_ingest.py` — call `upload_video` after download, store R2 URL

**Effort:** ~3 hours when R2 video bucket is ready.

---

## Execution order

| # | Fix | Effort | Risk | Do when |
|---|---|---|---|---|
| 1 | `trend_velocity` compute | 4h | Medium — new module, no schema change | Now |
| 2 | `min-instances: 1` | 5m | Zero | Now (next deploy) |
| 3 | Gemini retry backoff | 1h | Low | Now |
| 4 | `daily_free_query_count` gate | 2h | Low — fail-open design | Now |
| 5 | R2 permanent video URL | 3h | Medium — infra dependency | Month 2 |

Fixes 1–4 can be done in one backend session. Fix 5 is explicitly deferred.

---

## What this unblocks

After Fixes 1–4:
- ⑥ Trend Spike and ② Content Directions responses become **live-computed** from real corpus data, not seed rows
- Cold-start latency eliminated — first query of the day no longer penalized
- Batch runs survive transient Gemini errors
- Bot abuse on free intents is gated

After Fix 5 (Month 2):
- Explore video playback is permanent, zero-egress, fully offline from ED CDN

---

## Not in scope

- Layer 7 (Sound & Slang Radar) — no `sound_trends` table or compute. Worth adding to Wave 4 plan if EnsembleData exposes audio IDs in metadata.
- Monday email — P1-10 in project plan, separate feature work needed.
- `niche_intelligence` RPC verification — RPC exists in migration 16 with function body. Assumed correct unless niche norms show zeros in production.
