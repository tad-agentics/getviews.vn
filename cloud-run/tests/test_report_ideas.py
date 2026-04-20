"""Phase C.3 — Ideas report tests.

Coverage:
- Fixture path validates against §J `IdeasPayload` (standard variant, 5 ideas).
- Thin-corpus fixture reduces to 3 ideas + suppresses stop_doing.
- Hook-variants mode: variant flag set + stop_doing suppressed.
- `build_ideas_report` live entry:
    * variant="hook_variants" → hook_variants branch, regardless of DB state.
    * no service client → fixture fallback, window_days threaded through.
- Compute helpers:
    * rank_hooks_for_ideas ordering.
    * compute_ideas_blocks shape (5 items with prerequisites + confidence meta).
    * compute_style_cards fallback when style_distribution is empty.
    * compute_stop_doing empty when corpus is too thin (< 3 eligible hooks).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.report_ideas import (
    build_fixture_ideas_report,
    build_hook_variants_report,
    build_ideas_report,
    build_thin_corpus_ideas_report,
)
from getviews_pipeline.report_ideas_compute import (
    compute_ideas_blocks,
    compute_stop_doing,
    compute_style_cards,
    rank_hooks_for_ideas,
)
from getviews_pipeline.report_types import IdeasPayload, validate_and_store_report


# ── Fixture / thin / variant payload validation ──────────────────────────────


def test_fixture_ideas_validates() -> None:
    inner = build_fixture_ideas_report()
    p = IdeasPayload.model_validate(inner)
    assert p.variant == "standard"
    assert len(p.ideas) == 5
    assert len(p.style_cards) == 5
    assert len(p.stop_doing) == 5
    assert p.confidence.sample_size >= 60


def test_fixture_envelope_validates() -> None:
    inner = build_fixture_ideas_report()
    env = validate_and_store_report("ideas", inner)
    assert env["kind"] == "ideas"
    assert "report" in env


def test_thin_corpus_reduces_to_three_ideas() -> None:
    """sample_size < 60 → 3 ideas + no stop_doing (plan §2.2)."""
    inner = build_thin_corpus_ideas_report()
    p = IdeasPayload.model_validate(inner)
    assert p.confidence.sample_size < 60
    assert len(p.ideas) == 3
    assert p.stop_doing == []
    # Variant still defaults to standard so the UI knows to hide StopDoing only.
    assert p.variant == "standard"


def test_hook_variants_sets_variant_and_suppresses_stop_doing() -> None:
    inner = build_hook_variants_report(seed_hook="Mình vừa test ___ và")
    p = IdeasPayload.model_validate(inner)
    assert p.variant == "hook_variants"
    assert p.stop_doing == []
    # Hook callout + 2–3 bullets instead of 6-slide accordion.
    for idea in p.ideas:
        assert idea.hook, "hook callout must be populated in variant mode"
        assert 2 <= len(idea.slides) <= 3, "variant mode collapses slides to 2–3 bullets"


def test_hook_variants_falls_through_variant_string_gate() -> None:
    """build_ideas_report picks variant path regardless of DB availability."""
    inner = build_ideas_report(niche_id=1, query="test hook", intent_type="hook_variants", window_days=7, variant="hook_variants")
    p = IdeasPayload.model_validate(inner)
    assert p.variant == "hook_variants"
    assert p.stop_doing == []


def test_build_ideas_report_threads_window_days_on_fixture_fallback() -> None:
    """Without service client, fixture path returns a valid payload with the
    caller's window_days on the confidence strip."""
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_ideas_report(1, "test", "brief_generation", window_days=14, variant="standard")
    p = IdeasPayload.model_validate(inner)
    assert p.confidence.window_days == 14
    assert p.variant == "standard"


# ── Compute helpers ─────────────────────────────────────────────────────────


def _he_row(hook_type: str, views: float, ret: float, n: int, trend: str = "stable") -> dict[str, object]:
    return {
        "hook_type": hook_type,
        "avg_views": views,
        "avg_completion_rate": ret,
        "sample_size": n,
        "trend_direction": trend,
    }


def test_rank_hooks_for_ideas_orders_by_views_times_retention() -> None:
    rows = [
        _he_row("question", 1000, 0.4, 20),
        _he_row("bold_claim", 800, 0.7, 20),  # 800 * 0.7 = 560
        _he_row("curiosity_gap", 1200, 0.5, 20),  # 1200 * 0.5 = 600
    ]
    ranked = rank_hooks_for_ideas(rows)
    assert ranked[0]["hook_type"] == "curiosity_gap"
    assert ranked[1]["hook_type"] == "bold_claim"
    assert ranked[2]["hook_type"] == "question"


def test_compute_ideas_blocks_returns_5_with_required_fields() -> None:
    ranked = [
        _he_row(f"type_{i}", 1000 - i * 10, 0.7 - i * 0.02, 50 + i) for i in range(6)
    ]
    corpus = [
        {"video_id": f"v{i}", "hook_type": "type_0", "creator_handle": f"@c{i}", "views": 1000 - i}
        for i in range(3)
    ]
    blocks = compute_ideas_blocks(ranked, corpus, baseline_views=500.0)
    assert len(blocks) == 5
    for block in blocks:
        assert block.id
        assert block.title
        assert block.tag
        assert block.angle
        assert block.hook
        assert len(block.slides) >= 3
        assert block.metric["label"] == "RETENTION DỰ KIẾN"
        assert block.prerequisites  # at least one chip
        assert "sample_size" in block.confidence and "creators" in block.confidence


def test_compute_ideas_blocks_evidence_ids_join_corpus_by_hook_type() -> None:
    ranked = [_he_row("curiosity_gap", 900, 0.7, 40)]
    corpus = [
        {"video_id": "v1", "hook_type": "curiosity_gap", "creator_handle": "@a", "views": 200_000},
        {"video_id": "v2", "hook_type": "curiosity_gap", "creator_handle": "@b", "views": 150_000},
        {"video_id": "vX", "hook_type": "other", "creator_handle": "@c", "views": 180_000},
    ]
    blocks = compute_ideas_blocks(ranked, corpus, baseline_views=100_000.0)
    assert blocks[0].evidence_video_ids == ["v1", "v2"]


def test_compute_style_cards_falls_back_to_5_when_empty() -> None:
    cards = compute_style_cards([], n=5, fallback_niche="Tech")
    assert len(cards) == 5
    for c in cards:
        assert c["name"] and c["desc"]
        assert isinstance(c["paired_ideas"], list)


def test_compute_style_cards_uses_taxonomy_rows_when_present() -> None:
    sd = [
        {"name": "Niche Style A", "desc": "Mô tả A", "paired_ideas": ["#1"]},
        {"name": "Niche Style B", "desc": "Mô tả B"},
    ]
    cards = compute_style_cards(sd, n=5, fallback_niche="Tech")
    assert cards[0]["name"] == "Niche Style A"
    assert cards[1]["paired_ideas"] == ["#2"]  # fallback paired when row omits it


def test_compute_stop_doing_returns_bottom_5_by_retention() -> None:
    rows = [_he_row(f"hook_{i}", 1000, 0.9 - i * 0.1, 10) for i in range(6)]
    stop = compute_stop_doing(rows, baseline_views=500.0)
    assert len(stop) == 5
    assert stop[0]["bad"] and stop[0]["why"] and stop[0]["fix"]


def test_compute_stop_doing_empty_when_corpus_too_thin() -> None:
    """Plan §2.2 empty state: < 3 eligible hooks → no StopDoing section."""
    rows = [_he_row("only_one", 1000, 0.5, 10)]
    stop = compute_stop_doing(rows, baseline_views=500.0)
    assert stop == []


# ── Live pipeline smoke (mocked DB) ─────────────────────────────────────────


@patch("getviews_pipeline.report_ideas_compute.load_ideas_inputs")
def test_build_ideas_report_thin_niche_routes_to_thin_fixture(mock_load: MagicMock) -> None:
    """When ni.sample_size < 60, return the thin-corpus fixture shape."""
    mock_load.return_value = {
        "niche_label": "Tech",
        "ni": {"sample_size": 20, "organic_avg_views": 500},
        "he_rows": [
            _he_row("q", 500, 0.5, 10),
            _he_row("b", 400, 0.4, 10),
            _he_row("c", 300, 0.3, 10),
        ],
        "corpus": [],
        "style_distribution": [],
    }
    with patch("getviews_pipeline.supabase_client.get_service_client", return_value=MagicMock()):
        inner = build_ideas_report(5, "q", "brief_generation", window_days=7, variant="standard")
    p = IdeasPayload.model_validate(inner)
    assert p.confidence.sample_size < 60
    assert len(p.ideas) == 3
    assert p.stop_doing == []


@patch("getviews_pipeline.report_ideas_compute.load_ideas_inputs")
def test_build_ideas_report_full_corpus_returns_5_ideas(mock_load: MagicMock) -> None:
    corpus = [
        {"video_id": f"v{i}", "hook_type": f"type_{i%3}", "creator_handle": f"@c{i}", "views": 1000 - i}
        for i in range(30)
    ]
    mock_load.return_value = {
        "niche_label": "Tech",
        "ni": {"sample_size": 180, "organic_avg_views": 5000},
        "he_rows": [_he_row(f"type_{i}", 1000 - i * 20, 0.7 - i * 0.03, 30) for i in range(6)],
        "corpus": corpus,
        "style_distribution": [],
    }
    with patch("getviews_pipeline.supabase_client.get_service_client", return_value=MagicMock()):
        inner = build_ideas_report(5, "q", "brief_generation", window_days=7, variant="standard")
    p = IdeasPayload.model_validate(inner)
    assert p.variant == "standard"
    assert len(p.ideas) == 5
    assert p.confidence.sample_size == 180
    # Style cards always render 5; stop_doing non-empty since 6 eligible rows.
    assert len(p.style_cards) == 5
    assert len(p.stop_doing) == 5
    # Each idea has evidence_video_ids drawn from corpus (may be empty for some hooks).
    assert all(isinstance(i.evidence_video_ids, list) for i in p.ideas)


def test_envelope_rejects_unknown_variant_at_schema_boundary() -> None:
    """§J schema: variant ∈ {standard, hook_variants}; anything else fails validation."""
    inner = build_fixture_ideas_report()
    inner["variant"] = "freeform"
    with pytest.raises(ValueError):
        IdeasPayload.model_validate(inner)
