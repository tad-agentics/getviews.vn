"""D5c (2026-06-05) — Kho Douyin · weekly patterns orchestrator tests.

Mocks the Supabase client + ``synth_douyin_patterns`` so tests don't
touch network or DB. Mirrors the D3b test taxonomy.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

from getviews_pipeline.douyin_patterns_batch import (
    SYNTH_FRESH_FOR,
    DouyinPatternsBatchSummary,
    _avg_cn_rise_for_sample,
    _fetch_active_niches,
    _fetch_existing_week_rows,
    _fetch_niche_corpus,
    _iso_monday_utc,
    _upsert_pattern_rows,
    run_douyin_patterns_batch,
)
from getviews_pipeline.douyin_patterns_synth import (
    DouyinPatternEntry,
    DouyinPatternsSynth,
    DouyinPatternsSynthInputVideo,
)

# ── Helpers ─────────────────────────────────────────────────────────


def _chain(data: list[dict[str, Any]] | None = None) -> MagicMock:
    """A MagicMock that absorbs the entire fluent ``.select().eq().in_()
    .gte().order().limit().execute()`` chain used across the
    orchestrator's queries."""
    chain = MagicMock()
    for method in (
        "select", "eq", "in_", "gte", "order", "limit", "or_", "upsert",
    ):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = MagicMock(data=data or [])
    return chain


def _client(table_chains: dict[str, MagicMock]) -> MagicMock:
    """Returns a Supabase-client-shaped mock that dispatches each
    ``client.table(name)`` call to the chain registered for it."""
    client = MagicMock()
    client.table.side_effect = lambda name: table_chains[name]
    return client


def _input(video_id: str, **overrides: Any) -> DouyinPatternsSynthInputVideo:
    base = {
        "video_id": video_id,
        "title_zh": "睡前3件事",
        "title_vi": "3 việc trước khi ngủ",
        "hook_phrase": "睡前3件事",
        "hook_type": "curiosity_gap",
        "content_format": "voiceover_pov",
        "views": 500_000,
        "cn_rise_pct": 35.0,
    }
    base.update(overrides)
    return DouyinPatternsSynthInputVideo(**base)


def _entry(rank: int, video_ids: list[str]) -> DouyinPatternEntry:
    return DouyinPatternEntry(
        rank=rank,
        name_vn=f"Routine {rank} bước trước khi ngủ",
        name_zh="睡前仪式",
        hook_template_vi="3 việc trước khi ___ — 1 tháng sau bạn sẽ khác",
        format_signal_vi=(
            "Quay POV cận cảnh, transition cắt nhanh sau mỗi 1.5s, voiceover thì thầm."
        ),
        sample_video_ids=video_ids,
    )


def _synth(video_ids: list[str]) -> DouyinPatternsSynth:
    return DouyinPatternsSynth(patterns=[
        _entry(1, video_ids[:3]),
        _entry(2, video_ids[1:4]),
        _entry(3, video_ids[2:5]),
    ])


# ── _iso_monday_utc ────────────────────────────────────────────────


def test_iso_monday_utc_lands_on_monday_for_a_midweek_now() -> None:
    # Wed 2026-06-03 12:30 UTC → Mon 2026-06-01.
    now = datetime(2026, 6, 3, 12, 30, tzinfo=UTC)
    assert _iso_monday_utc(now).isoformat() == "2026-06-01"


def test_iso_monday_utc_returns_same_day_for_a_monday_now() -> None:
    now = datetime(2026, 6, 1, 0, 1, tzinfo=UTC)
    assert _iso_monday_utc(now).isoformat() == "2026-06-01"


def test_iso_monday_utc_rolls_back_for_a_sunday_now() -> None:
    now = datetime(2026, 6, 7, 22, 0, tzinfo=UTC)  # Sun
    assert _iso_monday_utc(now).isoformat() == "2026-06-01"


# ── _fetch_active_niches ───────────────────────────────────────────


def test_fetch_active_niches_filters_to_active_and_orders_id_asc() -> None:
    chain = _chain([{"id": 1, "slug": "wellness", "name_vn": "W", "name_zh": "Z"}])
    client = _client({"douyin_niche_taxonomy": chain})
    rows = _fetch_active_niches(client, niche_ids=None)
    chain.eq.assert_any_call("active", True)
    chain.order.assert_called_with("id", desc=False)
    assert rows[0]["slug"] == "wellness"


def test_fetch_active_niches_restricts_to_provided_ids() -> None:
    chain = _chain([])
    client = _client({"douyin_niche_taxonomy": chain})
    _fetch_active_niches(client, niche_ids=[2, 1, 1, 3])
    # in_() should receive a deduped sorted list.
    chain.in_.assert_called_with("id", [1, 2, 3])


def test_fetch_active_niches_returns_empty_on_query_error() -> None:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    chain.execute.side_effect = RuntimeError("PostgREST 500")
    client = _client({"douyin_niche_taxonomy": chain})
    assert _fetch_active_niches(client, niche_ids=None) == []


# ── _fetch_existing_week_rows ──────────────────────────────────────


def test_fetch_existing_week_rows_groups_by_niche_keeping_latest_ts() -> None:
    week = datetime(2026, 6, 1).date()
    chain = _chain([
        {"niche_id": 1, "computed_at": "2026-06-01T08:00:00+00:00"},
        {"niche_id": 1, "computed_at": "2026-06-02T08:00:00+00:00"},  # later
        {"niche_id": 2, "computed_at": "2026-06-01T09:00:00+00:00"},
    ])
    client = _client({"douyin_patterns": chain})
    out = _fetch_existing_week_rows(client, week_of=week)
    assert out[1].isoformat() == "2026-06-02T08:00:00+00:00"
    assert out[2].isoformat() == "2026-06-01T09:00:00+00:00"


def test_fetch_existing_week_rows_returns_empty_on_error() -> None:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.side_effect = RuntimeError("PostgREST 500")
    client = _client({"douyin_patterns": chain})
    assert _fetch_existing_week_rows(client, week_of=datetime(2026, 6, 1).date()) == {}


# ── _fetch_niche_corpus ────────────────────────────────────────────


def test_fetch_niche_corpus_orders_by_views_desc_with_lookback_cutoff() -> None:
    chain = _chain([
        {
            "video_id": "v1", "title_zh": "X", "title_vi": "X",
            "hook_phrase": "h", "hook_type": "ht", "content_format": "f",
            "views": 1000, "cn_rise_pct": 5.0,
        },
    ])
    client = _client({"douyin_video_corpus": chain})
    rows = _fetch_niche_corpus(client, niche_id=1, pool_size=10, lookback_days=7)
    chain.eq.assert_any_call("niche_id", 1)
    chain.order.assert_called_with("views", desc=True)
    chain.limit.assert_called_with(10)
    assert len(rows) == 1
    assert rows[0].video_id == "v1"
    assert rows[0].views == 1000
    assert rows[0].cn_rise_pct == 5.0


def test_fetch_niche_corpus_handles_null_cn_rise_pct() -> None:
    chain = _chain([
        {"video_id": "v1", "views": 100, "cn_rise_pct": None},
    ])
    client = _client({"douyin_video_corpus": chain})
    rows = _fetch_niche_corpus(client, niche_id=1, pool_size=10, lookback_days=7)
    assert rows[0].cn_rise_pct is None


def test_fetch_niche_corpus_skips_rows_with_empty_video_id() -> None:
    chain = _chain([
        {"video_id": "", "views": 100},
        {"video_id": "v1", "views": 200},
    ])
    client = _client({"douyin_video_corpus": chain})
    rows = _fetch_niche_corpus(client, niche_id=1, pool_size=10, lookback_days=7)
    assert len(rows) == 1
    assert rows[0].video_id == "v1"


# ── _avg_cn_rise_for_sample ────────────────────────────────────────


def test_avg_cn_rise_for_sample_means_known_values_only() -> None:
    pool = [
        _input("a", cn_rise_pct=10.0),
        _input("b", cn_rise_pct=30.0),
        _input("c", cn_rise_pct=None),
    ]
    assert _avg_cn_rise_for_sample(pool, ["a", "b", "c"]) == 20.0


def test_avg_cn_rise_for_sample_returns_none_when_all_null() -> None:
    pool = [_input("a", cn_rise_pct=None), _input("b", cn_rise_pct=None)]
    assert _avg_cn_rise_for_sample(pool, ["a", "b"]) is None


def test_avg_cn_rise_for_sample_returns_none_when_sample_outside_pool() -> None:
    pool = [_input("a", cn_rise_pct=10.0)]
    assert _avg_cn_rise_for_sample(pool, ["x", "y"]) is None


# ── _upsert_pattern_rows ───────────────────────────────────────────


def test_upsert_pattern_rows_writes_3_rows_with_avg_rise() -> None:
    chain = _chain([])
    client = _client({"douyin_patterns": chain})
    pool = [_input(f"v{i}", cn_rise_pct=20.0 + i) for i in range(5)]
    synth = _synth([v.video_id for v in pool])
    written = _upsert_pattern_rows(
        client,
        niche_id=1,
        week_of=datetime(2026, 6, 1).date(),
        synth=synth,
        pool=pool,
    )
    assert written == 3
    # Inspect the upsert payload: 3 rows, on_conflict on the composite key.
    call = chain.upsert.call_args
    payload = call.args[0]
    assert len(payload) == 3
    assert call.kwargs.get("on_conflict") == "niche_id,week_of,rank"
    ranks = sorted(p["rank"] for p in payload)
    assert ranks == [1, 2, 3]
    # cn_rise_pct_avg is set per row (mean of the sample's pool members).
    for row in payload:
        assert row["cn_rise_pct_avg"] is not None
        assert row["niche_id"] == 1
        assert row["week_of"] == "2026-06-01"


def test_upsert_pattern_rows_returns_zero_on_error() -> None:
    chain = MagicMock()
    chain.upsert.return_value = chain
    chain.execute.side_effect = RuntimeError("PostgREST 500")
    client = _client({"douyin_patterns": chain})
    pool = [_input(f"v{i}") for i in range(5)]
    synth = _synth([v.video_id for v in pool])
    out = _upsert_pattern_rows(
        client, niche_id=1, week_of=datetime(2026, 6, 1).date(),
        synth=synth, pool=pool,
    )
    assert out == 0


# ── run_douyin_patterns_batch ──────────────────────────────────────


def _orchestrator_client(
    *,
    niches: list[dict[str, Any]],
    existing: list[dict[str, Any]] | None = None,
    corpus_rows: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Wires distinct chains for the 3 tables the orchestrator hits.
    ``corpus_rows`` is reused for every niche (test data is uniform)."""
    niche_chain = _chain(niches)
    existing_chain = _chain(existing or [])
    corpus_chain = _chain(corpus_rows or [])
    return _client({
        "douyin_niche_taxonomy": niche_chain,
        "douyin_patterns": existing_chain,
        "douyin_video_corpus": corpus_chain,
    })


def test_orchestrator_skips_thin_pool() -> None:
    """Niches with < MIN_INPUT_POOL rows should be counted under
    ``skipped_thin_pool``, not ``failed_synth``."""
    client = _orchestrator_client(
        niches=[{"id": 1, "name_vn": "Wellness", "name_zh": "养生"}],
        corpus_rows=[
            {"video_id": f"v{i}", "views": 100, "cn_rise_pct": None}
            for i in range(3)
        ],
    )
    summary = run_douyin_patterns_batch(client, force=True)
    assert summary.considered_niches == 1
    assert summary.skipped_thin_pool == 1
    assert summary.failed_synth == 0
    assert summary.written_rows == 0


def test_orchestrator_skips_fresh_niches_when_force_false() -> None:
    """A niche with a row already written within ``SYNTH_FRESH_FOR``
    must be skipped (cron retry idempotence)."""
    fresh_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    client = _orchestrator_client(
        niches=[{"id": 1, "name_vn": "Wellness", "name_zh": "养生"}],
        existing=[{"niche_id": 1, "computed_at": fresh_ts}],
    )
    summary = run_douyin_patterns_batch(client, force=False)
    assert summary.skipped_fresh == 1
    assert summary.written_rows == 0


def test_orchestrator_recomputes_when_force_true() -> None:
    """``force=True`` bypasses the freshness short-circuit."""
    fresh_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    pool_rows = [
        {
            "video_id": f"v{i}", "title_zh": "X", "title_vi": "Y",
            "hook_phrase": "h", "hook_type": "ht", "content_format": "f",
            "views": 1000 - i, "cn_rise_pct": 30.0,
        }
        for i in range(8)
    ]
    client = _orchestrator_client(
        niches=[{"id": 1, "name_vn": "Wellness", "name_zh": "养生"}],
        existing=[{"niche_id": 1, "computed_at": fresh_ts}],
        corpus_rows=pool_rows,
    )
    expected_synth = _synth([r["video_id"] for r in pool_rows])
    with patch(
        "getviews_pipeline.douyin_patterns_batch.synth_douyin_patterns",
        return_value=expected_synth,
    ) as synth_mock:
        summary = run_douyin_patterns_batch(client, force=True)
    assert summary.skipped_fresh == 0
    assert summary.written_rows == 3
    assert synth_mock.call_count == 1


def test_orchestrator_records_failed_synth_when_pool_is_full_but_synth_returns_none() -> None:
    """Synth returns None for a non-thin pool ⇒ count as failed_synth,
    not skipped_thin_pool."""
    pool_rows = [
        {"video_id": f"v{i}", "views": 100, "cn_rise_pct": 5.0} for i in range(8)
    ]
    client = _orchestrator_client(
        niches=[{"id": 1, "name_vn": "Wellness", "name_zh": "养生"}],
        corpus_rows=pool_rows,
    )
    with patch(
        "getviews_pipeline.douyin_patterns_batch.synth_douyin_patterns",
        return_value=None,
    ):
        summary = run_douyin_patterns_batch(client, force=True)
    assert summary.skipped_thin_pool == 0
    assert summary.failed_synth == 1
    assert summary.written_rows == 0


def test_orchestrator_summary_has_week_of_iso_string() -> None:
    client = _orchestrator_client(niches=[])
    summary = run_douyin_patterns_batch(
        client, now=datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
    )
    assert summary.week_of == "2026-06-01"


def test_orchestrator_caps_at_max_niches() -> None:
    """``max_niches`` truncates the niche pool before any DB / Gemini
    calls happen — protects the wall-clock + cost budget."""
    niches = [
        {"id": i, "name_vn": f"Niche {i}", "name_zh": "中"} for i in range(1, 11)
    ]
    client = _orchestrator_client(niches=niches)
    summary = run_douyin_patterns_batch(client, max_niches=3, force=True)
    # 3 considered niches; all skipped_thin_pool because corpus is empty.
    assert summary.considered_niches == 3


def test_orchestrator_passes_niche_label_kwargs_to_synth() -> None:
    pool_rows = [
        {
            "video_id": f"v{i}", "title_zh": "X", "title_vi": "Y",
            "hook_phrase": "h", "hook_type": "ht", "content_format": "f",
            "views": 1000 - i, "cn_rise_pct": 30.0,
        }
        for i in range(8)
    ]
    client = _orchestrator_client(
        niches=[{"id": 9, "name_vn": "Công nghệ", "name_zh": "科技"}],
        corpus_rows=pool_rows,
    )
    expected_synth = _synth([r["video_id"] for r in pool_rows])
    with patch(
        "getviews_pipeline.douyin_patterns_batch.synth_douyin_patterns",
        return_value=expected_synth,
    ) as synth_mock:
        run_douyin_patterns_batch(client, force=True)
    _, kwargs = synth_mock.call_args
    assert kwargs["niche_name_vn"] == "Công nghệ"
    assert kwargs["niche_name_zh"] == "科技"
    assert len(kwargs["videos"]) == 8


def test_summary_dataclass_default_values() -> None:
    s = DouyinPatternsBatchSummary()
    assert s.considered_niches == 0
    assert s.written_rows == 0
    assert s.errors == []
    assert s.week_of is None


def test_synth_fresh_for_default_is_six_days() -> None:
    """Constant boundary — test guards against accidental tweak."""
    assert SYNTH_FRESH_FOR == timedelta(days=6)
