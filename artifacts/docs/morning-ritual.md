# Morning Ritual

Three ready-to-shoot TikTok scripts every creator wakes up to, generated
overnight and keyed to their niche + reference channels.

This is the hero feature of the Home screen (design's MorningRitual block).
Phase A · A2 ships the generator + endpoint + a banner in the existing
ChatScreen so we can validate the output before investing in the A3 Home
shell.

Implementations:
- `cloud-run/getviews_pipeline/morning_ritual.py`
- `supabase/migrations/20260423000050_daily_ritual.sql`
- `cloud-run/main.py::home_daily_ritual` + `::batch_morning_ritual`
- `src/hooks/useDailyRitual.ts`
- `src/routes/_app/components/MorningRitualBanner.tsx`

## Why

"Mở app ra, biết hôm nay quay gì" is the single-largest creator-value
shortcut this product can take. If we nail it, everything else — pulse,
ticker, Kênh Tham Chiếu — is supporting evidence for the Morning Ritual.

## Schema

Each row in `daily_ritual`:

```
user_id UUID              -- FK auth.users, cascade delete
generated_for_date DATE   -- UTC date the ritual is for
niche_id INTEGER          -- niche the user was in when generated
scripts JSONB             -- list of 3 RitualScript objects (see below)
adequacy TEXT             -- claim-tier of the grounding corpus slice
grounded_video_ids TEXT[] -- audit trail
generated_at TIMESTAMPTZ
PRIMARY KEY (user_id, generated_for_date)
```

Each RitualScript:

```
hook_type_en      Literal[...]  -- one of 19 canonical enum values
hook_type_vi      string        -- HOOK_TYPE_VI[hook_type_en]
title_vi          string        -- the hook line itself, ≤ 90 chars, quoted
why_works         string        -- 1 Vietnamese sentence, ≤ 140 chars
retention_est_pct int (30–90)
shot_count        int (2–8)
length_sec        int (15–90)
```

Validation is pydantic at generation time, so any row in `daily_ritual.scripts`
has already cleared the schema. The UI doesn't need to defend against malformed
data.

## Generation flow

`generate_ritual_for_user(client, user_id, niche_id, niche_name, reference_handles)`:

1. **Grounding ladder** — build a 10–20 video pool:
   - Primary: `video_corpus` rows in niche, created ≤ 7d ago, where
     `creator_handle IN reference_handles`
   - Fallback 1: niche-wide top-views last 7d
   - Fallback 2: niche-wide top-views last 30d
   - If still < 10 → return `thin_corpus` error; caller writes nothing

2. **Prompt** — `_PROMPT_TEMPLATE` injects:
   - Vietnamese niche name
   - Trimmed grounding JSON (just hook + hook_type + views per row)
   - Optional reference-handles note ("Ưu tiên giọng giống @a, @b")
   - Explicit requirement that the 3 scripts use **different** hook types

3. **Gemini call** with `response_json_schema = RitualBundle.model_json_schema()`
   so the output is structurally guaranteed. Temperature 0.6 — distinct
   scripts need some creativity.

4. **Post-processing**:
   - Defensive dedupe by `hook_type_en` (Gemini occasionally returns two
     `pov` despite the prompt rule). If < 3 distinct remain, treat as soft
     failure.
   - Enrich each script with `hook_type_vi` by mapping through `HOOK_TYPE_VI`.

5. **Upsert** to `daily_ritual` on `(user_id, generated_for_date)`.

`adequacy` comes from `claim_tiers.flags_for_count(pool_size).highest_passing_tier`
and is written alongside the scripts. The UI uses it to soften retention
claims on thin niches.

## Endpoints

### `GET /home/daily-ritual` (user-scoped)

Returns the most recent row for the calling user (≤ today). 404 when none
exists — the nightly cron runs at 07:00 ICT and new creators won't have a
row yet on day 0. The frontend renders a "sắp có" state for that case.

### `POST /batch/morning-ritual` (X-Batch-Secret gated)

Runs the nightly batch. Body:
```json
{ "user_ids": null }    // omit/null → all profiles with niche_id set
{ "user_ids": ["..."] } // smoke-test a specific set
```

Response:
```json
{
  "ok": true,
  "generated": 42,
  "skipped_thin": 3,
  "failed_schema": 1,
  "failed_gemini": 0,
  "users_no_niche": 5
}
```

**Cloud Scheduler wiring** (to add manually in GCP):
```
schedule:     "0 0 * * *"        # 07:00 ICT = 00:00 UTC
time zone:    "UTC"
target:       POST https://<service>/batch/morning-ritual
headers:      X-Batch-Secret: <BATCH_SECRET>
body:         {}
```

## UI integration (Phase A · A2)

`MorningRitualBanner` is rendered above the QUICK_ACTIONS grid on both the
mobile and desktop ChatScreen empty states. It:

- Reads `useDailyRitual()` — returns `null` if no ritual today (no banner renders)
- Shows 3 cards; the first is ink-filled (emphasis), the others are paper
- Each card click prefills the chat textarea with a shot-list prompt
  grounded in that script (`promptFromScript`) — submits via the existing
  chat stream
- Shows a "dữ liệu thưa" badge when `adequacy ∈ {none, reference_pool}`
  so the creator knows the retention numbers are directional

In A3 the banner relocates to the Home screen and card clicks route to the
Answer screen instead of the chat.

## Cost

One Gemini synthesis call per active creator per day.
Rough back-of-envelope on `GEMINI_SYNTHESIS_MODEL` with ~20 grounding videos:
- In: ~50k tokens
- Out: ~2k tokens
- ~$0.02/user/day

At 100 users: ~$2/day = ~$60/month.

## What Phase A validates

- Do creators click the cards?
- Do they return the next day to see new scripts?
- Are the scripts distinct enough day-to-day?
- Does the `adequacy` tier correctly soften messaging on thin niches?

If the answer is yes across the board, the A3 investment (Home shell +
tokens + onboarding step 2) is justified. If no, we rework the ritual (or
the grounding) before touching the shell.

## Testing

`cloud-run/tests/test_morning_ritual.py` covers grounding-ladder priorities,
prompt shape under reference / no-reference conditions, and the upsert
guard against errored results. The Gemini call itself is not exercised —
that's the job of CI's live-smoke on a staging project.

Frontend: `MorningRitualBanner` has no unit tests yet — it's a render-only
component with a single query hook. A Playwright flow against staging is
the right next test.

## Operator guidance

When the nightly batch runs, check the summary fields:

| Field | What it means | Action if elevated |
|---|---|---|
| `generated` | Successful writes | — |
| `skipped_thin` | Pool < 10 after all fallbacks | Expect 1–3 niches; persistent growth = corpus-health issue |
| `failed_schema` | Gemini returned invalid JSON | Check model version; if >5% of runs, tighten the prompt |
| `failed_gemini` | Gemini call itself errored | Network / quota; retry tomorrow |
| `users_no_niche` | Users haven't onboarded | Informational; surfaces onboarding-funnel leak |

`daily_ritual.grounded_video_ids` lets you reconstruct "why did we suggest
this script" after the fact.
