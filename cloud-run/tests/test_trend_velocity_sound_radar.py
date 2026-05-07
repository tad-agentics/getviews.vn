"""Sound Radar (L2.2 Sprint 2) — bucket math + delta computation tests.

These pin the Sound Radar compute helper directly so the bucket
thresholds and the new-this-week edge case stay stable as we tune
them. Integration with trend_velocity row assembly is covered in the
main run_trend_velocity test once we add it.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock


def _trending_rows(this_week: date, prev_week: date, *rows: dict) -> list[dict]:
    """Build the trending_sounds shape returned by Supabase ``.execute()``.

    Each ``row`` in ``*rows`` carries ``sound_id``, ``sound_name``,
    ``usage_count`` and which week it belongs to via ``week_label``
    ("tw" or "pw"). Resolves week_label to actual ISO week_of strings.
    """
    out: list[dict] = []
    for r in rows:
        wk = this_week.isoformat() if r["week_label"] == "tw" else prev_week.isoformat()
        out.append({
            "sound_id": r["sound_id"],
            "sound_name": r["sound_name"],
            "usage_count": r["usage_count"],
            "week_of": wk,
            "is_original_sound": r.get("is_original_sound", False),
        })
    return out


def _client_with_rows(rows: list[dict]) -> MagicMock:
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = SimpleNamespace(data=rows)
    return sb


def test_sound_radar_buckets_accelerating_when_delta_above_threshold() -> None:
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    tw = date(2026, 5, 4)
    pw = date(2026, 4, 27)

    rows = _trending_rows(
        tw, pw,
        {"sound_id": "s1", "sound_name": "Hot New Track", "usage_count": 18, "week_label": "tw"},
        {"sound_id": "s1", "sound_name": "Hot New Track", "usage_count": 6, "week_label": "pw"},  # +200%
    )
    out = _compute_sound_trends_for_niche(_client_with_rows(rows), niche_id=2, week_start=tw)

    assert len(out["accelerating"]) == 1
    assert out["accelerating"][0]["sound_id"] == "s1"
    assert out["accelerating"][0]["delta_pct"] == 200.0
    assert out["peaking"] == []
    assert out["cooling"] == []


def test_sound_radar_buckets_peaking_when_delta_within_band() -> None:
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    tw = date(2026, 5, 4)
    pw = date(2026, 4, 27)
    # 22 → 24 = +9% (within ±15) AND both weeks have ≥ 5 → peaking
    rows = _trending_rows(
        tw, pw,
        {"sound_id": "s1", "sound_name": "Stable Hit", "usage_count": 24, "week_label": "tw"},
        {"sound_id": "s1", "sound_name": "Stable Hit", "usage_count": 22, "week_label": "pw"},
    )
    out = _compute_sound_trends_for_niche(_client_with_rows(rows), niche_id=2, week_start=tw)

    assert out["accelerating"] == []
    assert len(out["peaking"]) == 1
    assert out["peaking"][0]["sound_id"] == "s1"
    assert out["cooling"] == []


def test_sound_radar_buckets_cooling_on_steep_decline() -> None:
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    tw = date(2026, 5, 4)
    pw = date(2026, 4, 27)
    # 4 → 24 (no, this is reverse): pw=24, tw=4 → -83% with pw≥5 → cooling
    rows = _trending_rows(
        tw, pw,
        {"sound_id": "s1", "sound_name": "Faded Sound", "usage_count": 4, "week_label": "tw"},
        {"sound_id": "s1", "sound_name": "Faded Sound", "usage_count": 24, "week_label": "pw"},
    )
    out = _compute_sound_trends_for_niche(_client_with_rows(rows), niche_id=2, week_start=tw)

    assert out["cooling"] and out["cooling"][0]["sound_id"] == "s1"
    assert out["accelerating"] == []
    assert out["peaking"] == []


def test_sound_radar_treats_brand_new_sound_as_accelerating_when_volume_meaningful() -> None:
    """No prev-week data + ≥3 uses this week = "new accelerating" — exactly the
    timing signal a creator wants to act on within the 48h window."""
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    tw = date(2026, 5, 4)
    pw = date(2026, 4, 27)
    rows = _trending_rows(
        tw, pw,
        {"sound_id": "s1", "sound_name": "Brand New", "usage_count": 9, "week_label": "tw"},
    )
    out = _compute_sound_trends_for_niche(_client_with_rows(rows), niche_id=2, week_start=tw)

    assert len(out["accelerating"]) == 1
    # Sentinel for "new" — JSON-serialisable, FE renders as "↑ +9999%" (or
    # short-circuits to "new" badge if it picks up the sentinel).
    assert out["accelerating"][0]["delta_pct"] == 9999.0
    assert out["accelerating"][0]["last_week"] == 0


def test_sound_radar_drops_low_volume_first_week_sounds() -> None:
    """A sound appearing only this week with < 3 uses isn't a trend yet
    — it's noise. Drop it instead of polluting accelerating."""
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    tw = date(2026, 5, 4)
    pw = date(2026, 4, 27)
    rows = _trending_rows(
        tw, pw,
        {"sound_id": "s_quiet", "sound_name": "Maybe", "usage_count": 1, "week_label": "tw"},
        {"sound_id": "s_quiet", "sound_name": "Maybe", "usage_count": 0, "week_label": "pw"},
    )
    out = _compute_sound_trends_for_niche(_client_with_rows(rows), niche_id=2, week_start=tw)

    assert out["accelerating"] == []
    assert out["peaking"] == []
    assert out["cooling"] == []


def test_sound_radar_ignores_original_sounds() -> None:
    """Originals = creator's own audio. Same rationale as L1.4 sound_mix —
    we recommend trending music, not surface that creators use their own."""
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    tw = date(2026, 5, 4)
    pw = date(2026, 4, 27)
    rows = _trending_rows(
        tw, pw,
        {"sound_id": "s_orig", "sound_name": "creator's own", "usage_count": 50, "week_label": "tw", "is_original_sound": True},
    )
    out = _compute_sound_trends_for_niche(_client_with_rows(rows), niche_id=2, week_start=tw)

    assert out["accelerating"] == []


def test_sound_radar_returns_empty_on_supabase_failure() -> None:
    """Any Supabase failure must be non-fatal — empty dict, FE falls back."""
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    sb = MagicMock()
    sb.table.side_effect = RuntimeError("supabase down")

    out = _compute_sound_trends_for_niche(sb, niche_id=2, week_start=date(2026, 5, 4))
    assert out == {}


def test_sound_radar_caps_each_bucket_at_top_5_by_volume() -> None:
    """Each bucket returns at most 5 entries, sorted by this_week (most-used first)."""
    from getviews_pipeline.trend_velocity import _compute_sound_trends_for_niche

    tw = date(2026, 5, 4)
    pw = date(2026, 4, 27)

    rows = []
    # 7 accelerating sounds — all >+50% delta with tw≥3
    for i in range(7):
        rows.extend([
            {"sound_id": f"a{i}", "sound_name": f"Acc {i}", "usage_count": 20 - i, "week_label": "tw"},
            {"sound_id": f"a{i}", "sound_name": f"Acc {i}", "usage_count": 5,       "week_label": "pw"},
        ])

    out = _compute_sound_trends_for_niche(
        _client_with_rows(_trending_rows(tw, pw, *rows)),
        niche_id=2, week_start=tw,
    )

    assert len(out["accelerating"]) == 5
    # Ordered by this_week desc — most-used first
    assert [e["sound_id"] for e in out["accelerating"]] == ["a0", "a1", "a2", "a3", "a4"]


# ── pattern_compute integration: top_sounds[].trend stamp ────────────────


def test_top_sounds_payload_stamps_trend_when_sound_id_in_lookup() -> None:
    from getviews_pipeline.report_pattern_compute import (
        _build_sound_trend_lookup,
        _top_sounds_payload,
    )

    sound_trends = {
        "accelerating": [{"sound_id": "x", "name": "Rising Track", "this_week": 12}],
        "peaking":      [{"sound_id": "y", "name": "Stable Hit",   "this_week": 24}],
        "cooling":      [{"sound_id": "z", "name": "Faded Tune",   "this_week": 4}],
    }
    lookup = _build_sound_trend_lookup(sound_trends)
    assert lookup == {"x": "accelerating", "y": "peaking", "z": "cooling"}

    rows = [
        {"sound_id": "x", "sound_name": "Rising Track", "usage_count": 12, "is_original_sound": False},
        {"sound_id": "y", "sound_name": "Stable Hit",   "usage_count": 24, "is_original_sound": False},
        {"sound_id": "w", "sound_name": "Unknown",      "usage_count": 8,  "is_original_sound": False},
    ]
    out = _top_sounds_payload(rows, sound_trends_by_id=lookup)

    assert out[0] == {"name": "Rising Track", "usage_count": 12, "trend": "accelerating"}
    assert out[1] == {"name": "Stable Hit",   "usage_count": 24, "trend": "peaking"}
    # Unknown sound is in trending_sounds but not in trend_velocity buckets — no trend stamp.
    assert out[2] == {"name": "Unknown",      "usage_count": 8}
    assert "trend" not in out[2]


def test_build_sound_trend_lookup_handles_missing_or_empty() -> None:
    from getviews_pipeline.report_pattern_compute import _build_sound_trend_lookup

    assert _build_sound_trend_lookup(None) == {}
    assert _build_sound_trend_lookup({}) == {}
    assert _build_sound_trend_lookup({"accelerating": [], "peaking": []}) == {}


def test_sound_cell_detail_uses_dang_noi_when_leader_accelerating() -> None:
    """When the #1 sound is accelerating, surface "đang nổi: X" instead of
    "top ngách: X" — the more action-oriented Vietnamese copy."""
    from getviews_pipeline.report_pattern_compute import _sound_cell_detail

    rows = [{"sound_id": "x", "sound_name": "Hot", "usage_count": 12, "is_original_sound": False}]
    detail = _sound_cell_detail(rows, sound_trends_by_id={"x": "accelerating"})
    assert detail == "đang nổi: Hot"

    # When leader is just peaking (or no trend), use the legacy "top ngách" copy.
    detail = _sound_cell_detail(rows, sound_trends_by_id={"x": "peaking"})
    assert detail == "top ngách: Hot"
