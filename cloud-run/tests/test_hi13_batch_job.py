"""HI-13 — batch job lifecycle helpers (offline mocks)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.gemini import (
    _batch_stats_dict,
    parse_batch_extraction_analysis_json,
    run_corpus_extraction_batch_file_job,
)


def test_parse_batch_extraction_analysis_json_strips_markdown_fence() -> None:
    text = '```json\n{"hook_analysis": {"hook_type": "question"}}\n```'
    parsed = parse_batch_extraction_analysis_json(text)
    assert parsed["hook_analysis"]["hook_type"] == "question"


def test_batch_stats_dict_reads_attributes() -> None:
    job = SimpleNamespace(
        batch_stats=SimpleNamespace(
            request_count=10,
            successful_request_count=8,
            failed_request_count=2,
        )
    )
    assert _batch_stats_dict(job) == {
        "request_count": 10,
        "successful_request_count": 8,
        "failed_request_count": 2,
    }


def test_run_corpus_batch_poll_timeout_cancels_and_skips_video_delete() -> None:
    """P1: non-terminal poll → cancel attempt → do not delete uploaded video Files."""
    client = MagicMock()
    running_state = SimpleNamespace(name="JOB_STATE_RUNNING")

    def _running_job() -> SimpleNamespace:
        return SimpleNamespace(
            name="batches/test-job",
            state=running_state,
            dest=None,
            error=None,
        )

    batch_job = _running_job()
    client.batches.create.return_value = batch_job
    client.batches.get.side_effect = lambda **_kw: _running_job()
    client.files.upload.return_value = SimpleNamespace(name="files/jsonl-input")

    records = [
        {
            "key": "vid1",
            "request": {"contents": [{"role": "user", "parts": [{"text": "x"}]}], "config": {}},
        }
    ]

    with patch("getviews_pipeline.gemini._get_client", return_value=client):
        with patch("getviews_pipeline.gemini.time.monotonic", side_effect=[0.0, 0.0, 100.0]):
            with patch("getviews_pipeline.gemini.time.sleep"):
                out = run_corpus_extraction_batch_file_job(
                    records=records,
                    display_name="test-shard",
                    poll_interval_s=0.01,
                    poll_max_s=5.0,
                    gemini_file_names=["files/video-a"],
                )

    assert out["ok"] is False
    assert out["job_error"] == "poll_timeout_or_stuck"
    client.batches.cancel.assert_called_once_with(name="batches/test-job")
    video_deletes = [
        c
        for c in client.files.delete.call_args_list
        if c.kwargs.get("name") == "files/video-a"
    ]
    assert video_deletes == []


def test_run_corpus_batch_success_deletes_video_files() -> None:
    client = MagicMock()
    succeeded = SimpleNamespace(name="JOB_STATE_SUCCEEDED")
    batch_job = SimpleNamespace(
        name="batches/ok",
        state=succeeded,
        dest=SimpleNamespace(file_name="files/results-jsonl"),
        error=None,
        batch_stats=SimpleNamespace(
            request_count=1,
            successful_request_count=1,
            failed_request_count=0,
        ),
    )
    client.batches.create.return_value = batch_job
    client.batches.get.return_value = batch_job
    client.files.upload.return_value = SimpleNamespace(name="files/in-jsonl")
    client.files.download.return_value = (
        b'{"key": "vid1", "response": {"candidates": [{"content": {"parts": '
        b'[{"text": "{\\"hook_analysis\\": {\\"hook_type\\": \\"question\\"}}"}]}}], '
        b'"usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 2}}}\n'
    )

    records = [{"key": "vid1", "request": {"contents": [], "config": {}}}]

    with patch("getviews_pipeline.gemini._get_client", return_value=client):
        with patch("getviews_pipeline.gemini_cost.log_gemini_call"):
            out = run_corpus_extraction_batch_file_job(
                records=records,
                display_name="test-ok",
                poll_interval_s=0.01,
                poll_max_s=1.0,
                gemini_file_names=["files/video-a"],
            )

    assert out["ok"] is True
    assert out["by_video_id"]["vid1"]["ok"] is True
    assert out["batch_stats"]["failed_request_count"] == 0
    client.files.delete.assert_any_call(name="files/video-a")
