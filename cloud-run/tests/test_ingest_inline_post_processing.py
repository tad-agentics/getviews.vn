"""Inline post-processing guard — scheduled shifts defer to cron."""

from __future__ import annotations

from getviews_pipeline.corpus_ingest import should_run_inline_ingest_post_processing


def test_manual_full_run_runs_inline_post_processing() -> None:
    assert should_run_inline_ingest_post_processing(
        aborted_early=False,
        ingest_shift=None,
    ) is True


def test_scheduled_shifts_skip_inline_post_processing() -> None:
    for shift in ("a", "b", "c"):
        assert should_run_inline_ingest_post_processing(
            aborted_early=False,
            ingest_shift=shift,
        ) is False


def test_aborted_early_skips_even_for_manual_run() -> None:
    assert should_run_inline_ingest_post_processing(
        aborted_early=True,
        ingest_shift=None,
    ) is False
