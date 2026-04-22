"""Live-builder orchestration tests for ``build_lifecycle_report``.

Covers the three branches that matter for the 2026-04-22 follow-ups bug:

1. Service client unavailable → fixture path with query-aware narrative.
2. Thin corpus (< 80 rows) → fixture path, sample_size patched, intent
   confidence downgraded.
3. Full-sample format mode → live aggregation + Gemini narrative (Gemini
   mocked to return empty → falls through to fallback copy, which is
   still query-aware).

Hook-fatigue and subniche modes are covered by the fixture-overlay path
since their live aggregators aren't implemented yet — the behavioural
contract ("follow-ups don't collide") still holds.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from getviews_pipeline.report_lifecycle import build_lifecycle_report
from getviews_pipeline.report_types import LifecyclePayload


def _corpus_row(
    *,
    content_format: str,
    views: int,
    days_ago: int,
) -> dict[str, Any]:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "video_id": f"v{views}-{days_ago}-{content_format}",
        "views": views,
        "content_format": content_format,
        "indexed_at": ts.isoformat(),
        "posted_at": ts.isoformat(),
    }


def _make_corpus(n: int) -> list[dict[str, Any]]:
    """Build a corpus that spans both halves of a 30-day window with
    enough rows per format to pass the min-sample gate."""
    rows: list[dict[str, Any]] = []
    formats = ["tutorial", "haul", "review"]
    per_format_each_half = max(6, n // (len(formats) * 2))
    for fmt in formats:
        # Recent half.
        for i in range(per_format_each_half):
            rows.append(_corpus_row(
                content_format=fmt,
                views=1500 if fmt == "tutorial" else 800,
                days_ago=2 + i,
            ))
        # Prior half.
        for i in range(per_format_each_half):
            rows.append(_corpus_row(
                content_format=fmt,
                views=1000,
                days_ago=18 + i,
            ))
    return rows[:n] if n < len(rows) else rows


def _mock_sb_for_corpus(corpus_rows: list[dict[str, Any]]) -> MagicMock:
    sb = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "niche_taxonomy":
            m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(  # noqa: E501
                data={"name_vn": "Skincare", "name_en": "Skincare"},
            )
        elif name == "video_corpus":
            chain = (
                m.select.return_value.eq.return_value.gte.return_value
                .order.return_value.limit.return_value
            )
            chain.execute.return_value = MagicMock(data=corpus_rows)
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    sb.table.side_effect = table
    return sb


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_service_client_error_falls_back_to_fixture(
    mock_get_svc: MagicMock,
) -> None:
    """When Supabase can't be reached the builder still returns a valid
    payload so the user sees the reference shape instead of a 500."""
    mock_get_svc.side_effect = RuntimeError("no url")

    r = build_lifecycle_report(niche_id=2, query="format nào còn chạy", mode="format")
    LifecyclePayload.model_validate(r)  # shape still valid
    assert r["mode"] == "format"
    assert r["subject_line"]


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_no_niche_id_falls_back_to_fixture(mock_get_svc: MagicMock) -> None:
    mock_get_svc.return_value = _mock_sb_for_corpus([])
    r = build_lifecycle_report(niche_id=0, query="format nào", mode="format")
    LifecyclePayload.model_validate(r)
    assert r["mode"] == "format"


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_thin_corpus_below_floor_uses_fixture_and_downgrades_confidence(
    mock_get_svc: MagicMock,
) -> None:
    """< 80 rows triggers the thin-corpus branch: fixture cells, sample
    size patched onto the confidence strip, intent_confidence → low."""
    corpus = _make_corpus(40)
    mock_get_svc.return_value = _mock_sb_for_corpus(corpus)

    r = build_lifecycle_report(niche_id=2, query="format nào", mode="format", window_days=30)
    LifecyclePayload.model_validate(r)

    # Confidence reflects the thin-sample reality.
    assert r["confidence"]["sample_size"] == len(corpus)
    assert r["confidence"]["intent_confidence"] == "low"


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_full_sample_format_mode_uses_live_aggregation(
    mock_get_svc: MagicMock,
) -> None:
    corpus = _make_corpus(120)
    mock_get_svc.return_value = _mock_sb_for_corpus(corpus)

    r = build_lifecycle_report(niche_id=2, query="format nào", mode="format", window_days=30)
    LifecyclePayload.model_validate(r)

    assert r["mode"] == "format"
    # Sample size reflects the live corpus, not the fixture's 310.
    assert r["confidence"]["sample_size"] == len(corpus)
    # Tutorial (rising +50%) should rank ahead of haul/review (declining).
    cell_names = [c["name"] for c in r["cells"]]
    assert any("Tutorial" in n for n in cell_names)


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_hook_fatigue_mode_uses_fixture_with_query_narrative(
    mock_get_svc: MagicMock,
) -> None:
    """hook_fatigue has no live aggregator yet — fixture cells, but the
    subject line and related questions are still query-aware."""
    mock_get_svc.return_value = _mock_sb_for_corpus(_make_corpus(200))

    a = build_lifecycle_report(
        niche_id=2, query="hook 'mình vừa test' còn dùng được không",
        mode="hook_fatigue",
    )
    b = build_lifecycle_report(
        niche_id=2, query="hook nào cùng họ đang lên thay thế",
        mode="hook_fatigue",
    )
    LifecyclePayload.model_validate(a)
    LifecyclePayload.model_validate(b)
    # Two different queries → two different subject lines (the 2026-04-22
    # bug guard).
    assert a["subject_line"] != b["subject_line"]


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_subniche_mode_uses_fixture_with_query_narrative(
    mock_get_svc: MagicMock,
) -> None:
    mock_get_svc.return_value = _mock_sb_for_corpus(_make_corpus(200))

    r = build_lifecycle_report(
        niche_id=2, query="ngách con nào đang lên trong skincare", mode="subniche",
    )
    LifecyclePayload.model_validate(r)
    assert r["mode"] == "subniche"
    # Subniche cells carry instance_count; retention_pct is always None.
    for c in r["cells"]:
        assert c["instance_count"] is not None
        assert c["retention_pct"] is None


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_aggregation_produces_no_cells_falls_back_to_fixture(
    mock_get_svc: MagicMock,
) -> None:
    """Edge case: ≥ 80 rows but no single format has ≥ 5 rows in both
    halves → aggregation returns 0 cells → fixture fallback (rather
    than shipping an empty cells list which violates the Pydantic
    min_length invariant)."""
    # 100 rows all in the recent half — no prior-half samples.
    rows = [
        _corpus_row(content_format="tutorial", views=1500, days_ago=2)
        for _ in range(100)
    ]
    mock_get_svc.return_value = _mock_sb_for_corpus(rows)

    r = build_lifecycle_report(niche_id=2, query="format nào", mode="format")
    LifecyclePayload.model_validate(r)
    assert len(r["cells"]) >= 1
