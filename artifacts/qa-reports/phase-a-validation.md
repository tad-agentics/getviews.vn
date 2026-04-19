# Phase A validation — playbook

Two goals: prove the redesigned Home screens read real data, and prove
the Morning Ritual generator produced at least one shootable bundle.
Everything below should be runnable in one sitting; expect ≤ 30 minutes.

Companion files:

- `artifacts/qa-reports/smoke-home.sh` — curl-based HTTP smoke test
- `artifacts/sql/phase-a-validation.sql` — paste into Supabase SQL Editor

## Preflight

Environment you need:

```bash
# Required for every step
export CLOUD_RUN_URL="https://<service>.run.app"

# Sign in as a real user in the web app → devtools → Session Storage →
# supabase.auth.token → copy the access_token value (long "eyJhbGci..." string)
export JWT="eyJhbGci..."

# Only needed if you want to trigger the ritual batch on-demand
export BATCH_SECRET="..."  # matches cloud-run env BATCH_SECRET
```

Also have the Supabase dashboard open to the right project and the SQL
Editor ready to paste into.

## Step 1 — Confirm migrations deployed

Paste section 1 of `phase-a-validation.sql`. Expected: rows with versions
`20260423000049` (phase_a_reference_channels) and `20260423000050`
(daily_ritual).

**If zero rows**: migrations weren't applied. Run `supabase db push` from
the repo, then re-run the playbook from here.

## Step 2 — Confirm schema shape

Paste section 2. Expect `profiles.reference_channel_handles` (TEXT[],
default `'{}'`), plus all 10 columns of `starter_creators` and all 7
columns of `daily_ritual`.

## Step 3 — Smoke the four /home/* reads

```bash
./artifacts/qa-reports/smoke-home.sh
```

Expected:

| Endpoint | Pass signal |
|---|---|
| `/home/pulse` | 200, `adequacy` ≠ `"none"` for a thick niche, `videos_this_week` > 0 |
| `/home/ticker` | 200, `items.length ≥ 3` (below that the marquee is hidden by design) |
| `/home/starter-creators` | 200, `creators.length ≤ 10` for the user's niche |
| `/home/daily-ritual` | 200 *or* 404 (404 is expected before the cron runs once) |

**If `/home/daily-ritual` returns 404**: nothing was generated for this
user today yet. Proceed to Step 4 to confirm the batch is actually
running.

**If any other endpoint 5xx's**: capture the exception from Cloud Run
logs and report back — most likely culprits are (a) stale Supabase
types causing a 500 on a missing column, (b) `get_service_client()`
SUPABASE_SERVICE_ROLE_KEY env missing.

## Step 4 — Has the nightly batch run?

Paste section 4 of `phase-a-validation.sql`. Expect at least one row
with `generated_for_date = current_date` for a recent date.

**If zero today**: Cloud Scheduler didn't fire, or it fired and the
endpoint 500'd, or every profile was too thin. Check the Cloud Run
logs for `[ritual]` entries, then run section 9 to see corpus depth.

### Manually trigger the batch for one user

If you want to force a generation right now instead of waiting for
tomorrow's cron:

```bash
# Resolve your own user_id from the JWT
USER_ID=$(curl -sS -H "Authorization: Bearer $JWT" "$CLOUD_RUN_URL/auth-check" | jq -r '.user_id')

# Trigger for just that user
curl -sS -X POST "$CLOUD_RUN_URL/batch/morning-ritual" \
  -H "X-Batch-Secret: $BATCH_SECRET" \
  -H "Content-Type: application/json" \
  -d "{\"user_ids\": [\"$USER_ID\"]}" | jq .
```

Expected response shape:

```json
{
  "ok": true,
  "generated": 1,
  "skipped_thin": 0,
  "failed_schema": 0,
  "failed_gemini": 0,
  "users_no_niche": 0
}
```

The `smoke-home.sh` script will do this for you if `BATCH_SECRET` is
exported.

## Step 5 — Is the ritual quality any good?

This is the whole Phase A bet. Paste section 7 of the SQL file. You get
a single row's `scripts` JSONB pretty-printed. Three questions to
answer by eye:

1. **Distinct hooks**: the three `hook_type_en` values should be
   different. If two are the same, the code drops the row and the
   batch counter skips it — you shouldn't see this in the data.
2. **Shootable**: would a creator in that niche actually record one of
   these tomorrow? If the titles read generic ("5 mẹo hay về X") or
   echo the grounding too literally ("Mình vừa test X"), prompt tuning
   is needed before we proceed.
3. **Retention estimates**: the `retention_est_pct` should sit in a
   realistic 40–80 range. Consistent 90s or consistent 40s = the
   prompt is nudging too hard in one direction.

## Step 6 — Onboarding funnel sanity

Paste section 8.

- `total_users` is your whole user base.
- `step_1_niche_set` is how many picked a niche (either via the
  pre-A3.5 modal or the new `/app/onboarding`).
- `step_2_references_set` is how many picked ≥ 1 reference channel.

A wide gap between step 1 and step 2 suggests users are skipping the
reference-channels step. The step is skippable by design
(ReferenceChannelsStep writes `[]` when the user clicks "Bỏ qua"),
so some gap is expected.

## Step 7 — Browser dogfood

Open an incognito window, sign in as a never-seen-before user or a
user where you've cleared `profiles.primary_niche` manually.

1. Land on `/app` → expect immediate redirect to `/app/onboarding`.
2. Pick a niche → auto-advance to step 2 (reference channels).
3. Pick 1–3 creators → click "Tiếp tục" → land on `/app` (Home).
4. On Home: ticker running, greeting reads "Chào {firstName}…",
   composer has chips, pulse card shows numbers, quick-actions grid
   renders, hooks table + breakouts populate if the niche is thick.
5. Click the composer → lands on `/app/chat` with the prompt prefilled.
6. Click a morning-ritual card → `/app/chat` with a shot-list prompt.
7. Hit the "Xu hướng" nav → `/app/trends` loads.
8. Hit the "Kênh tham chiếu" nav entry → should be greyed out
   ("Sắp có" badge, not clickable).
9. Mobile: narrow the window to < 900px — sidebar collapses, bottom
   tab bar appears with 4 items.

Capture anything that surprises you in a screenshot.

## Code audit — findings that won't show up in data

These were surfaced by reading `morning_ritual.py` end-to-end. None
block validation, but worth logging before Phase B.

### 1. `duplicate_hook_types` error has no counter

`run_morning_ritual_batch` counts `skipped_thin`, `failed_schema`, and
`failed_gemini` but not the `duplicate_hook_types` soft-failure. If
Gemini keeps returning 3 scripts with only 2 distinct hook types, those
rows silently disappear from the summary.

*Fix*: add a `failed_duplicates: int = 0` to `RitualBatchSummary` and
extend the `elif result.error.startswith("duplicate_hook_types")` arm
in the loop. One-line change; not urgent.

### 2. `upsert_ritual` swallows exceptions

If the `daily_ritual` table is missing, the wrong shape, or RLS blocks
the service-role write, `upsert_ritual` catches the exception, logs it,
and returns — but the caller already incremented `generated`. The
summary will report "generated 50" while zero rows were actually
written.

*Fix*: `upsert_ritual` should raise (or return a bool) and the caller
should only bump `generated` on true success. Medium priority; will
confuse debug cycles.

### 3. Grounding window is ingest-time, not post-time

`_fetch_grounding_videos` filters on `video_corpus.created_at` (the
ingest timestamp), not `video_corpus.posted_at` (TikTok's own post
time). Works fine as long as ingest is nightly — "7 days of ingest"
≈ "7 days of posts". If ingest cadence ever slips or runs behind,
the ritual will ground on older content than expected.

*Fix*: consider switching to `posted_at` once the Morning Ritual
proves valuable — behaviour change, not a defect. Note only.

## Reporting back

Paste into the chat:

1. Outputs from sections 4, 5, 6, 7 of the SQL script (you can redact
   `user_id` if needed).
2. `smoke-home.sh` output (or at minimum the adequacy + items_count
   lines).
3. Your subjective read on step 5 — shootable or not?
4. Anything weird from the browser dogfood.

I'll synthesise into a go/no-go for Phase B.
