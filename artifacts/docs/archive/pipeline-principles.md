> **ARCHIVED 2026-05-14** — Pipeline principles have been consolidated into `artifacts/docs/system-design.md` §12. The binding rules still apply — refer to `system-design.md` as the authoritative source going forward.

# GetViews Pipeline Architecture Principles

*Established 2026-05-13. Binding for all pipeline work. These principles govern `cloud-run/getviews_pipeline/`.*

---

## 1. Service Layer Is Mandatory

All business logic lives in `cloud-run/getviews_pipeline/services/`:

| Module | Owns |
|---|---|
| `services/extraction.py` | `run_extraction_core`, `async_run_extraction_core`, Gemini frame analysis |
| `services/diagnosis.py` | `run_video_diagnosis_core`, error extraction, retention modeling |
| `services/synthesis.py` | `synthesize_core`, narrative generation, format cards |
| `services/channel.py` | `fetch_channel_context_sync` (24h cached), creator comparison |
| `services/performance.py` | Performance tier classification, KPI enrichment |
| `services/references.py` | Corpus reference video selection |
| `services/corpus_quality.py` | `promote_on_demand_to_corpus`, `quality_tier`, cohort eligibility |

`pipelines.py` and `video_analyze.py` are **thin orchestrators** — they sequence calls to services. No business logic belongs there directly. If you're adding significant logic to `pipelines.py`, you're adding it to the wrong place.

---

## 2. Two Cores — One Extraction, One Diagnosis

The pipeline has exactly two execution cores with distinct responsibilities:

```
run_extraction_core(video_path) -> ExtractionResult
  ↓
  • Download video (R2 / temp)
  • Gemini vision analysis (gemini.analyze_video → analyze_aweme → _finish_analysis)
  • apply_timestamp_guards  (v4 hardening)
  • validate_transcript      (v4 hardening)
  • score_entry_cost         (v4 hardening)
  Returns: ExtractionResult (typed Pydantic + TS interface)

run_video_diagnosis_core(DiagnosisInput) -> DiagnosisResult
  ↓
  • extract_video_errors     (Gemini error extraction)
  • apply_rule_based_video_errors (v4 hardening)
  • structural parsing (retention curve, hook phases, segments)
  Returns: DiagnosisResult (typed Pydantic)
```

**Invariant: batch never calls `run_video_diagnosis_core`.** Batch ingest (`corpus_ingest`, `douyin_ingest`) calls `async_run_extraction_core` only. The diagnosis layer is user-facing (SSE) only.

**Invariant: `finalize_video_narrative_layer` is never called from batch.** It owns the expensive 2-Gemini-call synthesis + narrative and is only triggered by the user-facing SSE path.

CI enforcement: `tests/test_two_core_audit.py` checks these invariants on every run.

---

## 3. OpenTelemetry Is Mandatory at Boundary Points

Every external I/O boundary must be wrapped in a `telemetry.span()`:

- Gemini API calls (`gemini.py:_generate_content_models`)
- HTTP calls to EnsembleData, R2
- Supabase queries that are user-critical (diagnosis cache hit/miss)

Setup: `main.py` calls `telemetry.setup_telemetry()` + `telemetry.instrument_fastapi()` at startup. Spans export to Cloud Trace via OTLP gRPC. Set `OTEL_DISABLED=true` in test environments (done in `tests/conftest.py`).

---

## 4. No Per-Instance State

Cloud Run instances can scale to multiple replicas. No mutable module-level state is allowed except:

- `services/channel.py` in-process cache (`_channel_cache`): **explicitly documented as acceptable** because `min-instances=1` keeps a warm instance and the cache is bounded (500 entries, 24h TTL). The worst case on cache miss is a redundant Supabase query, not a crash.

Everything else must be stateless and safe to reconstruct on each request.

---

## 5. Schema Contract CI Test

`tests/test_schema_contract.py` auto-generates JSON Schema from Pydantic models and compares against TypeScript interfaces in `src/lib/api-types.ts`.

**Rule: any new Pydantic model that crosses the FE/BE boundary must:**
1. Have a matching TypeScript interface in `api-types.ts`
2. Pass the schema contract test before merging

Models covered: `ExtractionResult`, `VideoDiagnosisV5`, `VideoErrorsExtractionInput`, `DiagnosisSynthesisInput`.

---

## 6. Pydantic Settings — No `os.environ.get` in Logic

Environment variables are read once at import time via `getviews_pipeline/settings.py` (`pydantic.BaseSettings`). Business logic modules import from settings, never from `os.environ`. This provides fail-fast boot validation and makes all config dependencies explicit.

---

## 7. Cache-First for Repeated Work

Three cache layers, each with its own TTL and scope:

| Cache | TTL | Scope | Key |
|---|---|---|---|
| On-demand video cache (`video_diagnostics`) | 1h | per video | `tiktok_url` (canonical) |
| Corpus cache (`video_diagnostics` corpus rows) | 1h | per video | `video_id` |
| Channel snapshot (in-process) | 24h | per creator handle | `creator_handle` (normalized) |

**URL normalization is mandatory** before cache lookups. `normalize_tiktok_url()` strips query params, trailing slashes, and normalizes http→https, www prefix. This prevents spurious misses from URL variants.

**Cache miss cost:** on-demand = ~6min + Gemini cost. Cache hit = ~2s, $0 Gemini. Every cache miss that shouldn't have been a miss directly costs money.

---

## 8. COALESCE Provenance on UPSERT

`video_corpus.ingest_source` records how a row was first created: `batch_nightly`, `user_diagnosis`, or `douyin_batch`. This is **write-once** — the first writer sets it; subsequent upserts must not overwrite it.

**Mechanism:**
- `services/corpus_quality.py:promote_on_demand_to_corpus`: checks for existing row; only updates `last_refreshed_at` + `quality_tier` if row already exists.
- `corpus_ingest._upsert_rows_sync`: sets `ingest_source='batch_nightly'` by default; the DB function `upsert_video_corpus_batch` (migration `20260713000001`) uses `COALESCE(video_corpus.ingest_source, EXCLUDED.ingest_source)` so batch never overwrites user provenance.
- Dedup scope: `_existing_video_ids` and `_existing_video_ids_sync` are **globally scoped** (no niche filter). Per-niche scoping causes cross-niche dedup leaks (a video re-indexed in a different niche would re-run Gemini).

---

## 9. Structured Logging Is the Observability Backbone

Every critical event emits a structured JSON log via `observability.py`. Cloud Logging dashboards query by `jsonPayload.metric` or `jsonPayload.event`.

Required metrics (Phase 5.8):

| Metric | Event field | Emitted by |
|---|---|---|
| Cache hit rate | `cache_hit` / `cache_write` | `log_cache_event` in `video_analyze.py` |
| Gemini cost saved | `gemini_cost_saved_usd` | `log_diagnosis_event` in `pipelines.py` |
| Corpus growth via users | `corpus_growth` | `log_corpus_growth_event` in `corpus_quality.py` |
| Channel cache hit rate | `channel_cache_hit` / `channel_cache_miss` | `log_channel_cache_event` in `services/channel.py` |
| URL normalize collision | `url_normalize` | `log_url_normalize_event` in `video_analyze.py` |

---

## 10. LLM Input Contracts Are Typed and Auditable

Every Gemini call uses a Pydantic model for its structured data input, serialized as a JSON block in the prompt. This is the **HYBRID pattern**:

```
[Vietnamese rubric — natural language system instructions]
[JSON block — typed structured data, json.dumps(input_model)]
[Vietnamese format/output spec]
```

The input model is defined in `models.py` and tested by the schema contract CI. This makes regressions detectable without running Gemini: if the prompt changes a field name, the CI test fails before the change ships.

Input models: `VideoErrorsExtractionInput`, `DiagnosisSynthesisInput`.

---

## 11. v4 Hardening Is Non-Negotiable

These four guards apply to **every extraction path** without exception:

1. `apply_timestamp_guards`: strips impossible timestamps from error events.
2. `validate_transcript`: discards hallucinated transcripts.
3. `score_entry_cost`: scores entry cost based on hook timing.
4. `apply_rule_based_video_errors`: adds rule-based structural errors.

They live in the extraction core so all callers (batch + on-demand + diagnosis) receive them without per-caller duplication. Adding a new extraction path without routing through `run_extraction_core` will silently skip these guards — the audit test (`test_v4_hardening_uniform.py`) checks for this.

---

## Adding a New Pipeline

When adding a new pipeline (e.g., `instagram_ingest.py`):

1. **Extraction only:** call `async_run_extraction_core` or `run_extraction_core`. Never call `gemini.analyze_video` directly.
2. **Separate corpus table:** don't write to `video_corpus` unless the data is TikTok and belongs there.
3. **Service module:** add a `services/your_service.py` if the new pipeline has significant logic.
4. **Settings:** add any new env vars to `settings.py`, not `os.environ.get`.
5. **OTel span:** wrap every external I/O call.
6. **Schema contract:** if you add a Pydantic model that the FE needs, add the TS interface and extend the schema contract test.
7. **Audit test:** add a test to `test_two_core_audit.py` confirming the new module doesn't import diagnosis-layer symbols.
