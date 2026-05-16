# Gemini Batch API — research gate for HI-13

**Status:** NO-GO / deferred pending measured validation (2026-05-16 placeholder).

This note satisfies the `research-batch-api` plan item as a **staging document**. Promote to GO only after the checks below are filled with evidence from `google-genai` against a real extraction job.

## Go / no-go checklist (incomplete)

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Batch supports `response_json_schema` matching `VideoAnalysis` / carousel shape | TBD | |
| Video / Files API inputs acceptable in batch mode | TBD | |
| `thinking_budget=0` + `system_instruction` honored | TBD | |
| Per-item failure semantics (partial job success) | TBD | |
| Wall-clock: batch completes inside nightly ingest window | TBD | |
| Pricing: 50% discount applies to **video frame** input tokens | TBD | |

## Recommendation

**Default:** keep **live Files + SSE** path for corpus ingest until every row in the table above is PASS with production-like payloads. A failed gate (latency, schema, or pricing exclusion) blocks HI-13.

## References

- Google Gen AI SDK batch documentation (verify current SDK version in `cloud-run/pyproject.toml`).
- Internal: `cloud-run/getviews_pipeline/gemini.py` (`_generate_content_models`), `corpus_ingest.py` ingest loop.
