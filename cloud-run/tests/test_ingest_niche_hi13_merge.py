"""Regression — ingest_niche must propagate HI-13 metrics from _ingest_candidate_awemes."""

from __future__ import annotations

from getviews_pipeline.corpus_ingest import IngestResult, _merge_sub_ingest_result


def test_merge_sub_ingest_result_copies_hi13_counters() -> None:
    dst = IngestResult(ingest_loop_niche_id=1, niche_name="dst")
    src = IngestResult(
        ingest_loop_niche_id=1,
        niche_name="src",
        inserted=12,
        skipped=2,
        failed=1,
        subject_matter_inserted=5,
        errors=["e1"],
        hi13_batch_line_ok=14,
        hi13_batch_line_fail=1,
        hi13_sync_fallback=2,
        hi13_batch_jobs_ok=1,
        hi13_batch_jobs_failed=0,
    )
    _merge_sub_ingest_result(dst, src)
    assert dst.inserted == 12
    assert dst.skipped == 2
    assert dst.failed == 1
    assert dst.subject_matter_inserted == 5
    assert dst.errors == ["e1"]
    assert dst.hi13_batch_line_ok == 14
    assert dst.hi13_batch_line_fail == 1
    assert dst.hi13_sync_fallback == 2
    assert dst.hi13_batch_jobs_ok == 1
    assert dst.hi13_batch_jobs_failed == 0
