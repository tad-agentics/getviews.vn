"""L2.2 Sprint 3 — Sound Radar enrichment tests for morning_ritual.

Pins the contract for ``_fetch_sound_recommendations`` (the helper
that pulls accelerating/peaking buckets out of trend_velocity) and
the ``_urgency_band_for`` mapping. Integration with
``generate_ritual_for_user`` is covered by smoke-testing that
returned scripts carry the new sound fields when trend_velocity has
data, and don't when it doesn't.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.morning_ritual import (
    _fetch_sound_recommendations,
    _urgency_band_for,
)


# ── _urgency_band_for ────────────────────────────────────────────────────


def test_urgency_band_maps_accelerating_to_post_within_48h() -> None:
    assert _urgency_band_for("accelerating") == "post_within_48h"


def test_urgency_band_maps_peaking_to_this_week() -> None:
    assert _urgency_band_for("peaking") == "this_week"


def test_urgency_band_returns_none_for_cooling_or_unknown() -> None:
    """Cooling sounds get no recommendation strip — we don't surface
    them in the morning_ritual at all (they're for "skip these")."""
    assert _urgency_band_for("cooling") is None
    assert _urgency_band_for(None) is None
    assert _urgency_band_for("anything_else") is None


# ── _fetch_sound_recommendations ─────────────────────────────────────────


def _client_with_sound_trends(sound_trends: dict[str, Any] | None) -> MagicMock:
    sb = MagicMock()
    rows = [{"sound_trends": sound_trends, "week_start": "2026-05-04"}] if sound_trends is not None else []
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(data=rows)
    return sb


def test_fetch_recommendations_prefers_accelerating_over_peaking() -> None:
    sb = _client_with_sound_trends({
        "accelerating": [
            {"sound_id": "a1", "name": "Hot Track A", "delta_pct": 200.0},
        ],
        "peaking": [
            {"sound_id": "p1", "name": "Stable B", "delta_pct": 5.0},
        ],
        "cooling": [
            {"sound_id": "c1", "name": "Faded C", "delta_pct": -80.0},
        ],
    })

    out = _fetch_sound_recommendations(sb, niche_id=2, limit=3)

    # Accelerating first, then peaking. Cooling is never returned.
    assert len(out) == 2
    assert out[0]["sound_id"] == "a1"
    assert out[0]["sound_velocity"] == "accelerating"
    assert out[0]["urgency_band"] == "post_within_48h"
    assert out[1]["sound_id"] == "p1"
    assert out[1]["sound_velocity"] == "peaking"
    assert out[1]["urgency_band"] == "this_week"


def test_fetch_recommendations_caps_at_limit() -> None:
    sb = _client_with_sound_trends({
        "accelerating": [
            {"sound_id": f"a{i}", "name": f"Acc {i}", "delta_pct": 100.0 + i}
            for i in range(5)
        ],
        "peaking": [],
        "cooling": [],
    })

    out = _fetch_sound_recommendations(sb, niche_id=2, limit=3)
    assert len(out) == 3
    assert [r["sound_id"] for r in out] == ["a0", "a1", "a2"]


def test_fetch_recommendations_strips_brand_new_sentinel_delta() -> None:
    """delta_pct=9999 sentinel from _compute_sound_trends_for_niche
    (brand-new sound, no prev-week data) becomes None on the FE so we
    don't render a misleading "+9999%" string."""
    sb = _client_with_sound_trends({
        "accelerating": [
            {"sound_id": "new1", "name": "Brand New", "delta_pct": 9999.0},
        ],
        "peaking": [],
        "cooling": [],
    })

    out = _fetch_sound_recommendations(sb, niche_id=2, limit=3)
    assert len(out) == 1
    assert out[0]["sound_velocity"] == "accelerating"
    assert out[0]["sound_delta_pct"] is None  # sentinel scrubbed
    assert out[0]["urgency_band"] == "post_within_48h"


def test_fetch_recommendations_returns_empty_when_no_trend_velocity_row() -> None:
    sb = _client_with_sound_trends(None)  # zero rows
    assert _fetch_sound_recommendations(sb, niche_id=2) == []


def test_fetch_recommendations_returns_empty_when_sound_trends_empty() -> None:
    sb = _client_with_sound_trends({"accelerating": [], "peaking": [], "cooling": []})
    assert _fetch_sound_recommendations(sb, niche_id=2) == []


def test_fetch_recommendations_returns_empty_on_supabase_error() -> None:
    sb = MagicMock()
    sb.table.side_effect = RuntimeError("supabase down")
    assert _fetch_sound_recommendations(sb, niche_id=2) == []
    # And a None client path — used by tests / any caller without a service client.
    assert _fetch_sound_recommendations(None, niche_id=2) == []


def test_fetch_recommendations_skips_entries_with_no_sound_id() -> None:
    """Entries lacking ``sound_id`` are dropped (no usable handle for the
    FE handoff). When ``name`` is missing but ``sound_id`` is present,
    we fall back to using sound_id as the display name — better than
    dropping a real recommendation just because the upstream aggregator
    forgot to copy the name through."""
    sb = _client_with_sound_trends({
        "accelerating": [
            {"sound_id": "good", "name": "OK Track", "delta_pct": 100.0},
            {"sound_id": "", "name": "No id — drop me", "delta_pct": 50.0},
            {"sound_id": "fallback_named", "delta_pct": 50.0},  # no name → uses sid
        ],
        "peaking": [],
        "cooling": [],
    })
    out = _fetch_sound_recommendations(sb, niche_id=2, limit=5)
    assert {r["sound_id"] for r in out} == {"good", "fallback_named"}
    fallback = next(r for r in out if r["sound_id"] == "fallback_named")
    assert fallback["sound_name"] == "fallback_named"  # sid used as display
