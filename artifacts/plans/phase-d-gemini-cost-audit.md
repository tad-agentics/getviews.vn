# Phase D.0.ii — Gemini cost audit

**Date:** 2026-04-20
**Status:** Call-site inventory locked; live spend data pending (requires production log pull)
**Feeds:** D.2.5 (`response_format` binding on Pattern), D.5.1 (cost dashboard)

---

## Call-site inventory

`_generate_content_models` is the single Gemini SDK entrypoint
(`cloud-run/getviews_pipeline/gemini.py:141-165`). Every Gemini call
goes through it; `call_site` can be added as a kwarg when D.5.1 wires
the cost dashboard.

### Paid `/answer` turn path (per-turn call sites)

| # | Call site | Module:line | Model var | Purpose | JSON-bound today? |
|---|---|---|---|---|---|
| 1 | `classify_intent_gemini` | `gemini.py:613-693` | `GEMINI_INTENT_MODEL` (flash-lite) | Intent classification fallback (only on medium/low confidence from deterministic pass) | ✅ `response_mime_type="application/json"` + manual `json.loads` |
| 2 | `fill_pattern_narrative` | `report_pattern_gemini.py:fill_pattern_narrative` | `GEMINI_SYNTHESIS_MODEL` | Pattern thesis + 3 hook insights + 2-3 stalled insights + 4 related questions | ⚠️ `response_mime_type` set; manual `json.loads`, no pydantic binding |
| 3 | `fill_generic_narrative` | `report_generic_gemini.py:fill_generic_narrative` | `GEMINI_SYNTHESIS_MODEL` (via `gemini_text_only`) | Generic 1–2 paragraph hedged narrative | ⚠️ `response_mime_type` set; manual `json.loads` |
| 4 | (placeholder — not yet wired) | `report_ideas.py` (deterministic today) | — | Ideas `angle`/`why_works`/`slides` bodies | Not yet a Gemini call site |

**Paid-turn tally per format:**

- **Pattern primary turn:** call sites 1 (if classifier confidence
  medium/low) + 2. Worst case: 2 Gemini calls.
- **Ideas primary turn:** call site 1 (same condition). Narrative is
  deterministic today — 0–1 Gemini calls.
- **Timing primary turn:** call site 1 only. 0–1 Gemini calls.
- **Generic primary turn:** call sites 1 + 3. Worst case: 2 calls.
  Generic is free per C.0.5 credit rule (no billing); cost exposure
  but no revenue.

### Non-`/answer` Gemini paths (included for completeness; out of scope for D.0.ii cost projection)

| Module | Purpose |
|---|---|
| `channel_analyze.py:411-440` | Channel formula + lessons synthesis (B.3) |
| `video_analyze.py:*` | Video diagnosis headline + subtext + lessons (B.1) |
| `script_generate.py` | (D.1.2 Gemini upgrade target — post-D.0) |
| `thumbnail_analysis.py:*` | Video corpus ingest path (Cloud Scheduler batch) |
| `morning_ritual.py:*` | Nightly batch (Cloud Scheduler 22:00 ICT) |
| `layer0_sound.py` / `layer0_hashtag.py` / `layer0_migration.py` | Corpus ingest classifier (Cloud Scheduler batch) |

These share the same `_generate_content_models` entrypoint; `call_site`
attribution in D.5.1 needs to cover them all to keep the monthly ceiling
honest.

---

## Model env mapping (`cloud-run/getviews_pipeline/config.py:23-32`)

```python
GEMINI_MODEL             → default synthesis model  (env override)
GEMINI_EXTRACTION_MODEL  → frame extraction / layer0 classifier
GEMINI_SYNTHESIS_MODEL   → Pattern / Generic / video narrative
GEMINI_KNOWLEDGE_MODEL   → per-niche knowledge injection
GEMINI_DIAGNOSIS_MODEL   → flop-mode video diagnosis (defaults to SYNTHESIS)
GEMINI_INTENT_MODEL      → intent classifier (defaults to KNOWLEDGE / Flash-Lite)
```

Per `CLAUDE.md` LLM rules (Gemini 3.x only; no 2.5 / 2.0): current
defaults should resolve to `gemini-3-flash-preview` for synthesis and
`gemini-3-flash-lite-preview` for extraction / classifier. Verify env
configs in production during D.5.1.

---

## Pricing projection (approximate)

Gemini 3.x preview pricing as of 2026-04 (Google Cloud Console, per 1M
tokens):

| Model class | Input | Output |
|---|---|---|
| Flash-Lite | $0.25 | $1.50 |
| Flash | $0.50 | $3.00 |

**Per-turn worst case (Pattern primary with full narrative):**

- Classifier: 100 tok in + 50 tok out on Flash-Lite = ~$0.0001
- Pattern narrative: 1,200 tok in + 600 tok out on Flash = ~$0.0024
- **Total per paid Pattern turn: ~$0.0025**

**CLAUDE.md ceiling: ~$70/mo across all Gemini usage.**

At ~$0.0025/turn, the ceiling covers ~28,000 paid turns/month before
batch (morning ritual + corpus ingest) is even counted. For the batch
path (Cloud Scheduler nightly), token volume per niche × 21 niches
drives the bulk of the monthly spend; D.5.1 must instrument those call
sites first.

**Conclusion:** the `/answer` hot path is not the cost risk. The batch
paths (morning_ritual, corpus_ingest, thumbnail_analysis, layer0_*)
almost certainly dominate. D.5.1 dashboard must group by `call_site`
so the split is legible.

---

## Tighten-or-leave decisions per call site

### 1. `classify_intent_gemini` — LEAVE

Already guarded by `ClassifierDailyBudgetExceeded`. Deterministic
fallback on budget exhaustion. Flash-Lite is the cheapest model. No
change in D.

### 2. `fill_pattern_narrative` — TIGHTEN in D.2.5

Swap manual `json.loads(_strip_json(text))` for pydantic
`response_format` binding. Upside:

- Gemini API enforces the schema; malformed responses fail at SDK
  boundary not runtime.
- Token spend drops slightly because the model stops emitting prose
  around the JSON.
- Aligns with the §J WhatStalled invariant story — invariants are
  enforced at schema boundary not application code.

Implementation: add `response_schema` to the `config` dict in
`gemini.py:_extraction_json_config` pattern; apply to the narrative
call in `report_pattern_gemini.fill_pattern_narrative`. ~5-line
change. Fallback: if binding fails (empty response, API rejection),
call deterministic `build_why_won_list` — same code path that handles
Gemini errors today.

### 3. `fill_generic_narrative` — ADD BUDGET GUARD in D.2.5

Generic is always free (per C.0.5), so cost exposure without revenue
offset. D.2.5 wraps this call in a sibling `ClassifierDailyBudgetExceeded`
pattern keyed to `generic_narrative`; when exceeded, falls through to
the deterministic hedging copy that already exists in
`report_generic._generate_narrative`.

### 4. Ideas narrative — LEAVE

Deterministic today (see `phase-c-design-audit-ideas.md` Should-fix
#1). Adding a Gemini narrative is feature work and violates the Phase
D hard stop. Stay deterministic in D.

### 5. Batch paths (morning_ritual, corpus_ingest, layer0_*) — INSTRUMENT in D.5.1

These are the cost risk. D.5.1 dashboard adds `call_site` attribution
via a wrapper on `_generate_content_models`. Actionable decisions about
tightening batch paths happen after the dashboard produces 14 days of
real data — out of scope for Phase D proper; flagged here so D.5.1
ships the telemetry that enables the future decision.

---

## Production spend verification (pending)

Real spend data requires a production log pull:

1. Sample 50 `answer_turns` rows over 14 days (post-C close).
2. Pull matching Cloud Run logs (`[gemini-call]` — D.5.1 adds this
   log line; today use the raw `_generate_content_models` invocation
   timestamps as a proxy).
3. Tally `tokens_in` / `tokens_out` per call site.
4. Compare to the projection above. Flag anomalies.

**Placeholder — waiting on prod log pull (D.5.1 dashboard landing
fills this in).**

| Call site | Projected tokens/turn | Actual tokens/turn | Notes |
|---|---|---|---|
| `classify_intent_gemini` | 100 in / 50 out | — | |
| `fill_pattern_narrative` | 1,200 in / 600 out | — | |
| `fill_generic_narrative` | 400 in / 280 out | — | |

---

## Sign-off

Call-site inventory locked. Tighten-or-leave decisions recorded:
D.2.5 tightens Pattern narrative (pydantic binding) + wraps Generic
in budget guard; Ideas + classifier stay as-is; batch paths get
instrumented in D.5.1.

**Deliverable merged; feeds D.2.5 + D.5.1. Unblocks D.1 kickoff.**
