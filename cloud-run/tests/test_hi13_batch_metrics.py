"""HI-13 — ingest metrics accumulator."""

from __future__ import annotations

from getviews_pipeline.corpus_ingest import IngestResult, _apply_hi13_batch_metrics


def test_apply_hi13_batch_metrics_counts_hits_and_fallback() -> None:
    result = IngestResult(ingest_loop_niche_id=1, niche_name="test")
    vres = [("ok", [], []), ("ok", [], []), RuntimeError("fail")]
    batch_meta = {
        "ok": True,
        "by_video_id": {
            "v1": {"ok": True},
            "v2": {"ok": False, "error": "empty"},
            "v3": {"ok": True},
        },
    }
    _apply_hi13_batch_metrics(result, vres, batch_meta)
    assert result.hi13_batch_jobs_ok == 1
    assert result.hi13_batch_line_ok == 2
    assert result.hi13_batch_line_fail == 1
    assert result.hi13_sync_fallback == 0
