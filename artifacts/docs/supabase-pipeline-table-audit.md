# Supabase tables × GetViews pipeline audit

**Scope.** “Pipeline” here means **Cloud Run** (`cloud-run/main.py` + `cloud-run/getviews_pipeline/**/*.py`) using the **Supabase Python client** (`client.table(...)`, `sb.rpc(...)`, service-role where noted). It does **not** claim full coverage of **SPA** (`src/**` direct Supabase), **Vercel `api/*.ts`**, or **Supabase Edge Functions** (`supabase/functions/**`) — those are summarized in a separate column where relevant.

**Schema source.** `supabase/migrations/*.sql` (as of repo `main`). `niche_intelligence` is a **materialized view**, not a base table.

---

## Legend

| Tag | Meaning |
|-----|---------|
| **R** | Pipeline reads |
| **W** | Pipeline writes (insert/update/upsert/delete) |
| **—** | No direct `.table("…")` use in Cloud Run Python |
| **Edge** | Supabase Edge Function touches this object |
| **SPA** | Browser client reads/writes (typical pattern) |
| **RPC** | Invoked via `client.rpc(...)` from Cloud Run |

---

## Base tables & materialized view

| Object | Type | Cloud Run | Notes |
|--------|------|-----------|--------|
| `answer_sessions` | table | **R/W** | `answer_session.py` — session CRUD, list, archive fields |
| `answer_turns` | table | **R/W** | `answer_session.py` — append turns, stream finalize |
| `anonymous_usage` | table | **—** | Landing IP gate per migrations; not referenced in `cloud-run/` Python |
| `batch_failures` | table | **—** | Northstar / tech-spec; **no** `cloud-run` references |
| `channel_formulas` | table | **R/W** | `channel_analyze.py` — read user context, service upsert |
| `chat_archival_audit` | table | **—** / **Edge** | Nightly archival: `supabase/functions/cron-chat-archival` |
| `chat_messages` | table | **W** | `main.py`, `session_store.py`; **SPA/api** for chat UX |
| `chat_sessions` | table | **—** / **Edge** / **SPA** | Legacy chat; archival Edge deletes; **not** Cloud Run batch |
| `creator_velocity` | table | **R/W** | `batch_analytics.py`, `kol_browse.py` |
| `credit_transactions` | table | **—** / **SPA** / **Edge** | Ledger: `src/hooks/useCreditTransactions.ts`, payment webhooks — **not** `main.py` `.table()` |
| `cross_creator_patterns` | table | **W** | `cross_creator.py` |
| `daily_ritual` | table | **R/W** | `morning_ritual.py`, `main.py` |
| `draft_scripts` | table | **R/W** | `script_save.py` |
| `format_lifecycle` | table | **—** / **SPA** | `src/hooks/useFormatLifecycle.ts` reads; **no** Cloud Run writer (see `trend_velocity.py` TODO comment) |
| `gemini_calls` | table | **W** | `gemini_cost.py` — service_role inserts |
| `hashtag_niche_map` | table | **R/W** | `layer0_hashtag.py`, `hashtag_niche_map.py` |
| `hook_effectiveness` | table | **R/W** | `signal_classifier.py`, `batch_analytics.py`, report compute modules |
| `llm_cache` | table | **—** / **Edge** | `cron-monday-email` reads/writes |
| `niche_candidates` | table | **R/W** | `layer0_hashtag.py` |
| `niche_insights` | table | **R/W** | `layer0_niche.py`, `layer0_migration.py`, `pipelines.py` |
| `niche_taxonomy` | table | **R/W** | Widespread: corpus, layer0, reports, `morning_ritual.py`, etc. |
| `niche_intelligence` | **MV** | **R** + **refresh** | Read: `corpus_context.py`, `report_*_compute.py`, `video_niche_benchmark.py`, `script_data.py`, `main.py` niche fetch. **Refresh:** `corpus_ingest.py` → `rpc("refresh_niche_intelligence")` |
| `processed_webhook_events` | table | **—** / **Edge** | `payos-webhook`, `cron-prune-webhooks` |
| `profiles` | table | **R/W** | `main.py` (`is_processing`, `primary_niche`), `morning_ritual.py`, `kol_browse.py`, `channel_analyze.py` |
| `scene_intelligence` | table | **R/W** | `scene_intelligence_refresh.py`, `script_data.py` |
| `signal_grades` | table | **R/W** | `signal_classifier.py`, `corpus_context.py`, `trending_cards.py` |
| `starter_creators` | table | **R** | `main.py`, `channel_analyze.py`, `kol_browse.py` |
| `subscriptions` | table | **—** / **Edge** | `create-payment`, `cron-expiry-check` |
| `trend_velocity` | table | **R/W** | `trend_velocity.py` |
| `trending_cards` | table | **R/W** | `trending_cards.py`; **Edge** `cron-monday-email` |
| `trending_sounds` | table | **R/W** | `layer0_sound.py`, `sound_aggregator.py`, `pipelines.py`, `ticker.py` |
| `usage_events` | table | **W** | `answer_session.py` server-emits (e.g. classifier / pattern empty); **SPA** `logUsage` for product analytics |
| `video_corpus` | table | **R/W** | Dominant: ingest, layer0, analyze, reports, thumbnails, comment radar, etc. |
| `video_dang_hoc` | table | **R/W** | `video_dang_hoc.py` |
| `video_diagnostics` | table | **R/W** | `video_analyze.py` |
| `video_patterns` | table | **R/W** | `pattern_fingerprint.py`, `pulse.py`, `ticker.py`, `main.py` admin paths |

---

## RPCs used from Cloud Run (not tables)

| RPC | Used in |
|-----|---------|
| `decrement_credit` | `main.py` |
| `increment_free_query_count` | `main.py` |
| `refresh_niche_intelligence` | `corpus_ingest.py` |
| `toggle_reference_channel` | `main.py` (KOL pin flow) |

---

## Gaps & risks (pipeline lens)

1. **`format_lifecycle` / `batch_failures`** — Created in corpus migration; **no Cloud Run Python** references today. `format_lifecycle` is read in SPA; `batch_failures` appears unused in code (spec debt).
2. **`anonymous_usage`** — Still in schema for anonymous funnel; **not** in Cloud Run grep; likely **Edge/landing only** or future path — confirm before relying on it in batch jobs.
3. **`credit_transactions`** — Ledger consistency is **RPC/Edge + SPA**, not mirrored in `main.py` direct table writes; correct if design is “no client balance update without ledger row”.
4. **`chat_sessions`** — Cloud Run comment says session tracking in Supabase; **Python** mostly touches `chat_messages` + archival is **Edge**. History/search SQL functions (`history_union`, `search_history_union`) read `chat_sessions` server-side — not `.table()` in Python.
5. **`niche_intelligence`** — Single source of truth for norms; **stale MV** if ingest skips `refresh_niche_intelligence` after bulk upserts (see `corpus_ingest.py` flags).

---

## Non-pipeline consumers (sanity)

| Area | Tables / objects |
|------|-------------------|
| **Edge** | `subscriptions`, `profiles`, `processed_webhook_events`, `chat_sessions`, `chat_messages`, `chat_archival_audit`, `llm_cache`, `trending_cards` |
| **Vercel API** | `profiles`, `chat_messages`, `hook_effectiveness`, `video_corpus` (`api/*.ts`) |
| **SPA** | Most user-facing reads + `usage_events` inserts, `credit_transactions`, `format_lifecycle`, etc. |

---

## How to re-audit

```bash
# Tables from migrations
rg "CREATE TABLE" supabase/migrations --no-heading -o | sort -u

# Cloud Run table() calls
rg '\.table\(["\'][a-z_]+["\']' cloud-run --glob '*.py'

# Edge
rg '\.from\(["\'][a-z_]+["\']' supabase/functions --glob '*.ts'
```

**Last reviewed:** generated from repository state at audit time; re-run after adding migrations or new `getviews_pipeline` modules.
