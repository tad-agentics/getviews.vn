"""D3b (2026-06-04) — Kho Douyin · adapt-synth batch orchestrator tests.

Mocks the Supabase client + ``synth_douyin_adapt`` so tests don't hit
network / DB. Covers the orchestration shape — staleness query, niche-
label batched join, per-row synth, upsert, summary aggregation, and
the no-title skip path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.douyin_adapt_batch import (
    DouyinAdaptBatchSummary,
    SYNTH_STALE_AFTER,
    _fetch_niche_labels,
    _fetch_stale_corpus_rows,
    run_douyin_adapt_batch,
)
from getviews_pipeline.douyin_synth import DouyinAdaptSynth, TranslatorNote


# ── Fixtures ─────────────────────────────────────────────────────────


def _stale_chain(rows: list[dict[str, Any]]) -> MagicMock:
    """Mock for the ``douyin_video_corpus`` SELECT chain."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.or_.return_value = chain
    chain.in_.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.update.return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    return chain


def _client_with_table_chain(chain: MagicMock) -> MagicMock:
    client = MagicMock()
    client.table.return_value = chain
    return client


def _valid_synth() -> DouyinAdaptSynth:
    return DouyinAdaptSynth(
        adapt_level="green",
        adapt_reason="Wellness universal, không phụ thuộc văn hoá CN.",
        eta_weeks_min=2, eta_weeks_max=4,
        sub_vi="3 việc trước khi ngủ — 1 tháng sau bạn sẽ khác",
        translator_notes=[
            TranslatorNote(tag="TỪ NGỮ", note="睡前 = trước khi ngủ, dùng tự nhiên hơn 'tối nào cũng'."),
            TranslatorNote(tag="NHẠC NỀN", note="Đổi remix Jay Chou → piano slow VN, tránh copyright."),
        ],
    )


# ── _fetch_stale_corpus_rows ─────────────────────────────────────────


def test_stale_fetch_filters_by_synth_computed_at_freshness() -> None:
    chain = _stale_chain([{"video_id": "v1", "niche_id": 1, "title_zh": "X"}])
    client = _client_with_table_chain(chain)
    rows = _fetch_stale_corpus_rows(client, cap=50)
    assert len(rows) == 1
    # The OR clause must reference the freshness window cutoff.
    or_args, _ = chain.or_.call_args
    or_clause = str(or_args[0])
    assert "synth_computed_at.is.null" in or_clause
    assert "synth_computed_at.lt." in or_clause
    # Cutoff should be ~SYNTH_STALE_AFTER ago.
    cutoff_iso = or_clause.split("synth_computed_at.lt.")[1]
    cutoff_ts = datetime.fromisoformat(cutoff_iso)
    expected = datetime.now(timezone.utc) - SYNTH_STALE_AFTER
    assert abs((cutoff_ts - expected).total_seconds()) < 5


def test_stale_fetch_returns_empty_on_query_error() -> None:
    """Defensive: a Supabase HTTP error must NOT crash the batch — the
    summary stays at considered=0 and the next cron retries."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.or_.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.side_effect = RuntimeError("PostgREST 500")
    client = MagicMock()
    client.table.return_value = chain
    out = _fetch_stale_corpus_rows(client, cap=50)
    assert out == []


# ── _fetch_niche_labels ─────────────────────────────────────────────


def test_niche_labels_batched_into_one_query() -> None:
    """N rows touching M unique niches → ONE batched SELECT (no N+1)."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.in_.return_value = chain
    chain.execute.return_value = MagicMock(data=[
        {"id": 1, "name_vn": "Wellness", "name_zh": "养生"},
        {"id": 2, "name_vn": "Beauty", "name_zh": "美妆"},
    ])
    client = MagicMock()
    client.table.return_value = chain
    out = _fetch_niche_labels(client, [1, 2, 1, 2, 1])  # duplicates
    # Single ``in_`` call with the deduped sorted list.
    chain.in_.assert_called_once_with("id", [1, 2])
    assert out[1] == {"name_vn": "Wellness", "name_zh": "养生"}
    assert out[2] == {"name_vn": "Beauty", "name_zh": "美妆"}


def test_niche_labels_returns_empty_on_query_error() -> None:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.in_.return_value = chain
    chain.execute.side_effect = RuntimeError("PostgREST 500")
    client = MagicMock()
    client.table.return_value = chain
    out = _fetch_niche_labels(client, [1, 2])
    assert out == {}


def test_niche_labels_returns_empty_on_no_ids() -> None:
    """Don't waste a DB round-trip when there are no rows."""
    client = MagicMock()
    out = _fetch_niche_labels(client, [])
    assert out == {}
    client.table.assert_not_called()


# ── run_douyin_adapt_batch — happy path ──────────────────────────────


def test_batch_run_synth_and_upsert_for_each_stale_row() -> None:
    rows = [
        {"video_id": "v1", "niche_id": 1, "title_zh": "睡前3件事",
         "title_vi": None, "hook_phrase": None, "hook_type": None,
         "content_format": None, "synth_computed_at": None},
        {"video_id": "v2", "niche_id": 2, "title_zh": "护肤routine",
         "title_vi": "Routine chăm sóc da", "hook_phrase": None,
         "hook_type": None, "content_format": None, "synth_computed_at": None},
    ]

    # Two table.return_value chains — one for stale fetch, one for
    # niche labels, plus update chain for each upsert. Easiest to share
    # the same MagicMock with side_effect tuned per call.
    fetch_chain = _stale_chain(rows)
    niche_chain = MagicMock()
    niche_chain.select.return_value = niche_chain
    niche_chain.in_.return_value = niche_chain
    niche_chain.execute.return_value = MagicMock(data=[
        {"id": 1, "name_vn": "Wellness", "name_zh": "养生"},
        {"id": 2, "name_vn": "Beauty", "name_zh": "美妆"},
    ])
    update_chain = MagicMock()
    update_chain.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MagicMock(data=None)

    table_calls: list[str] = []

    def _table_router(name: str) -> MagicMock:
        table_calls.append(name)
        # First douyin_video_corpus call = stale fetch; subsequent calls
        # are upserts.
        if name == "douyin_video_corpus":
            if table_calls.count("douyin_video_corpus") == 1:
                return fetch_chain
            return update_chain
        if name == "douyin_niche_taxonomy":
            return niche_chain
        return MagicMock()

    client = MagicMock()
    client.table.side_effect = _table_router

    with patch(
        "getviews_pipeline.douyin_adapt_batch.synth_douyin_adapt",
        return_value=_valid_synth(),
    ):
        summary = run_douyin_adapt_batch(client, cap=10)

    assert summary.considered == 2
    assert summary.generated == 2
    assert summary.failed_synth == 0
    assert summary.failed_upsert == 0
    # Niche taxonomy hit once (batched), corpus table hit 1 fetch + 2 upserts.
    assert table_calls.count("douyin_niche_taxonomy") == 1
    assert table_calls.count("douyin_video_corpus") == 3


def test_batch_run_skips_rows_with_no_title_zh() -> None:
    """Row literally has nothing to grade — skip + stamp
    ``synth_computed_at`` so we don't re-poll it tomorrow."""
    rows = [
        {"video_id": "v1", "niche_id": 1, "title_zh": "",
         "title_vi": None, "hook_phrase": None, "hook_type": None,
         "content_format": None, "synth_computed_at": None},
    ]
    fetch_chain = _stale_chain(rows)
    niche_chain = MagicMock()
    niche_chain.select.return_value = niche_chain
    niche_chain.in_.return_value = niche_chain
    niche_chain.execute.return_value = MagicMock(data=[])
    update_chain = MagicMock()
    update_chain.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MagicMock(data=None)

    table_calls: list[str] = []

    def _router(name: str) -> MagicMock:
        table_calls.append(name)
        if name == "douyin_video_corpus":
            if table_calls.count("douyin_video_corpus") == 1:
                return fetch_chain
            return update_chain
        return niche_chain

    client = MagicMock()
    client.table.side_effect = _router

    with patch(
        "getviews_pipeline.douyin_adapt_batch.synth_douyin_adapt",
        return_value=None,
    ) as synth_mock:
        summary = run_douyin_adapt_batch(client, cap=10)

    assert summary.considered == 1
    assert summary.skipped_no_title == 1
    assert summary.generated == 0
    # Synth never called for empty title.
    synth_mock.assert_not_called()
    # synth_computed_at still stamped (so we don't re-poll daily).
    update_chain.update.assert_called_once()
    payload = update_chain.update.call_args[0][0]
    assert "synth_computed_at" in payload


def test_batch_run_increments_failed_synth_when_synth_returns_none() -> None:
    """Gemini failure / Pydantic validation error returns None — the
    orchestrator counts it under ``failed_synth`` and moves on."""
    rows = [
        {"video_id": "v1", "niche_id": 1, "title_zh": "睡前3件事",
         "title_vi": None, "hook_phrase": None, "hook_type": None,
         "content_format": None, "synth_computed_at": None},
    ]
    fetch_chain = _stale_chain(rows)
    niche_chain = MagicMock()
    niche_chain.select.return_value = niche_chain
    niche_chain.in_.return_value = niche_chain
    niche_chain.execute.return_value = MagicMock(data=[
        {"id": 1, "name_vn": "Wellness", "name_zh": "养生"},
    ])

    def _router(name: str) -> MagicMock:
        if name == "douyin_video_corpus":
            return fetch_chain
        return niche_chain

    client = MagicMock()
    client.table.side_effect = _router

    with patch(
        "getviews_pipeline.douyin_adapt_batch.synth_douyin_adapt",
        return_value=None,
    ):
        summary = run_douyin_adapt_batch(client, cap=10)

    assert summary.considered == 1
    assert summary.failed_synth == 1
    assert summary.generated == 0


def test_batch_run_video_ids_overrides_staleness_query() -> None:
    """``video_ids=[...]`` runs an explicit ``in_`` query, not the
    staleness ``or_`` — admin manual reruns after a synth-prompt bump."""
    fetch_chain = MagicMock()
    fetch_chain.select.return_value = fetch_chain
    fetch_chain.in_.return_value = fetch_chain
    fetch_chain.execute.return_value = MagicMock(data=[])
    client = MagicMock()
    client.table.return_value = fetch_chain

    summary = run_douyin_adapt_batch(client, video_ids=["v1", "v2"])
    assert summary.considered == 0
    fetch_chain.in_.assert_called_once_with("video_id", ["v1", "v2"])
    # No staleness OR clause.
    fetch_chain.or_.assert_not_called()


def test_batch_run_returns_empty_summary_when_no_stale_rows() -> None:
    """Don't run niche-label fetch / synth if there are no rows."""
    fetch_chain = _stale_chain([])
    client = _client_with_table_chain(fetch_chain)
    with patch(
        "getviews_pipeline.douyin_adapt_batch.synth_douyin_adapt",
    ) as synth_mock:
        summary = run_douyin_adapt_batch(client, cap=50)
    assert summary.considered == 0
    assert summary.generated == 0
    synth_mock.assert_not_called()


def test_batch_run_isolates_per_row_failures() -> None:
    """Two rows: one synth succeeds, one fails. Summary tracks both."""
    rows = [
        {"video_id": "v1", "niche_id": 1, "title_zh": "睡前3件事",
         "title_vi": None, "hook_phrase": None, "hook_type": None,
         "content_format": None, "synth_computed_at": None},
        {"video_id": "v2", "niche_id": 1, "title_zh": "失眠救星",
         "title_vi": None, "hook_phrase": None, "hook_type": None,
         "content_format": None, "synth_computed_at": None},
    ]
    fetch_chain = _stale_chain(rows)
    niche_chain = MagicMock()
    niche_chain.select.return_value = niche_chain
    niche_chain.in_.return_value = niche_chain
    niche_chain.execute.return_value = MagicMock(data=[
        {"id": 1, "name_vn": "Wellness", "name_zh": "养生"},
    ])
    update_chain = MagicMock()
    update_chain.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MagicMock(data=None)

    calls: list[str] = []

    def _router(name: str) -> MagicMock:
        calls.append(name)
        if name == "douyin_video_corpus":
            if calls.count("douyin_video_corpus") == 1:
                return fetch_chain
            return update_chain
        return niche_chain

    client = MagicMock()
    client.table.side_effect = _router

    # First call → success, second → None (synth failure).
    side_effect = [_valid_synth(), None]
    with patch(
        "getviews_pipeline.douyin_adapt_batch.synth_douyin_adapt",
        side_effect=side_effect,
    ):
        summary = run_douyin_adapt_batch(client, cap=10)

    assert summary.considered == 2
    assert summary.generated == 1
    assert summary.failed_synth == 1
