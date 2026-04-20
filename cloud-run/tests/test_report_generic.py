"""Phase C.5 — Generic report tests.

Coverage:
- Fixture validates against §J `GenericPayload` and envelope.
- `cap_paragraphs` enforces 2 × 320-char limit with sentence-boundary
  truncation + filters empty strings.
- `build_off_taxonomy_payload` returns the three static suggestions in
  fixed order.
- `pick_broad_evidence` dedupes by creator + caps at `limit`.
- `build_generic_report`:
    * no service client → fixture fallback.
    * broad corpus → real evidence + truncated narrative.
    * always ``intent_confidence == "low"``.
    * always emits exactly 3 off_taxonomy suggestions.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.report_generic import (
    build_fixture_generic_report,
    build_generic_report,
)
from getviews_pipeline.report_generic_compute import (
    NARRATIVE_MAX_PARAGRAPHS,
    NARRATIVE_PARAGRAPH_MAX_CHARS,
    OFF_TAXONOMY_SUGGESTIONS,
    build_off_taxonomy_payload,
    cap_paragraphs,
    pick_broad_evidence,
)
from getviews_pipeline.report_types import GenericPayload, validate_and_store_report


# ── Fixture / envelope ─────────────────────────────────────────────────────


def test_fixture_generic_validates() -> None:
    inner = build_fixture_generic_report()
    p = GenericPayload.model_validate(inner)
    assert p.confidence.intent_confidence == "low"
    assert len(p.off_taxonomy.get("suggestions", [])) == 3
    assert len(p.evidence_videos) == 3
    assert p.confidence.niche_scope is None
    paras = p.narrative.get("paragraphs", [])
    assert 1 <= len(paras) <= NARRATIVE_MAX_PARAGRAPHS
    for para in paras:
        assert len(para) <= NARRATIVE_PARAGRAPH_MAX_CHARS


def test_fixture_envelope_validates() -> None:
    env = validate_and_store_report("generic", build_fixture_generic_report())
    assert env["kind"] == "generic"
    assert "report" in env


# ── cap_paragraphs ────────────────────────────────────────────────────────


def test_cap_paragraphs_enforces_2_entries() -> None:
    paras = cap_paragraphs(["a.", "b.", "c.", "d."])
    assert len(paras) == NARRATIVE_MAX_PARAGRAPHS


def test_cap_paragraphs_filters_empty_strings() -> None:
    paras = cap_paragraphs(["  ", "has content.", "", "   "])
    assert paras == ["has content."]


def test_cap_paragraphs_truncates_on_sentence_boundary() -> None:
    long = (
        "Sentence one ends here. Sentence two continues with more content "
        "that pushes well past the limit and should be dropped. "
    ) * 8
    out = cap_paragraphs([long])
    assert len(out) == 1
    assert len(out[0]) <= NARRATIVE_PARAGRAPH_MAX_CHARS
    # Sentence-boundary truncation ends with punctuation, never mid-word.
    assert out[0].rstrip().endswith(("." , "!", "?", "…")) or out[0].endswith("…")


def test_cap_paragraphs_handles_unpunctuated_input() -> None:
    long = "word " * 200  # no punctuation at all
    out = cap_paragraphs([long])
    assert len(out) == 1
    assert len(out[0]) <= NARRATIVE_PARAGRAPH_MAX_CHARS


# ── off_taxonomy ──────────────────────────────────────────────────────────


def test_off_taxonomy_has_three_suggestions_in_fixed_order() -> None:
    payload = build_off_taxonomy_payload()
    sugg = payload["suggestions"]
    assert len(sugg) == 3
    assert [s["label"] for s in sugg] == [s["label"] for s in OFF_TAXONOMY_SUGGESTIONS]
    for s in sugg:
        assert s["route"].startswith("/app/")
        assert s["icon"]


def test_off_taxonomy_suggestions_are_copies_not_references() -> None:
    """Mutating the returned suggestions must not poison the static list."""
    payload = build_off_taxonomy_payload()
    payload["suggestions"][0]["label"] = "mutated"
    again = build_off_taxonomy_payload()
    assert again["suggestions"][0]["label"] != "mutated"


# ── pick_broad_evidence ───────────────────────────────────────────────────


def test_pick_broad_evidence_dedupes_by_creator_and_caps() -> None:
    rows = [
        {"video_id": "v1", "views": 1000, "creator_handle": "@a"},
        {"video_id": "v2", "views": 900, "creator_handle": "@a"},  # dedup
        {"video_id": "v3", "views": 800, "creator_handle": "@b"},
        {"video_id": "v4", "views": 700, "creator_handle": "@c"},
        {"video_id": "v5", "views": 600, "creator_handle": "@d"},
    ]
    out = pick_broad_evidence(rows, limit=3)
    assert [r["video_id"] for r in out] == ["v1", "v3", "v4"]


def test_pick_broad_evidence_drops_zero_view_rows() -> None:
    rows = [
        {"video_id": "v1", "views": 0, "creator_handle": "@a"},
        {"video_id": "v2", "views": 500, "creator_handle": "@b"},
    ]
    out = pick_broad_evidence(rows, limit=3)
    assert [r["video_id"] for r in out] == ["v2"]


# ── build_generic_report — live entry paths ───────────────────────────────


def test_build_generic_report_threads_window_days_on_fallback() -> None:
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_generic_report(None, "test query", window_days=21)
    p = GenericPayload.model_validate(inner)
    assert p.confidence.window_days == 21
    assert p.confidence.intent_confidence == "low"


def test_build_generic_report_never_sets_niche_scope() -> None:
    """Generic is the humility fallback — niche_scope MUST stay null so the
    FALLBACK chip renders correctly (plan §2.4 design spec)."""
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_generic_report(5, "test", window_days=14)
    p = GenericPayload.model_validate(inner)
    assert p.confidence.niche_scope is None


@patch("getviews_pipeline.report_generic._load_broad_corpus")
def test_build_generic_report_empty_corpus_routes_to_fixture(mock_load: MagicMock) -> None:
    mock_load.return_value = []
    with patch("getviews_pipeline.supabase_client.get_service_client", return_value=MagicMock()):
        inner = build_generic_report(None, "test", window_days=7)
    p = GenericPayload.model_validate(inner)
    # Fixture path always returns 3 evidence tiles + 3 off_taxonomy chips.
    assert len(p.evidence_videos) == 3
    assert len(p.off_taxonomy["suggestions"]) == 3


@patch("getviews_pipeline.report_generic._load_broad_corpus")
def test_build_generic_report_full_corpus_returns_live_evidence(mock_load: MagicMock) -> None:
    base_iso = "2026-04-18T00:00:00+00:00"
    mock_load.return_value = [
        {
            "video_id": f"v{i}",
            "creator_handle": f"@c{i}",
            "views": 50_000 - i * 1_000,
            "hook_type": "talking_head",
            "engagement_rate": 0.5,
            "video_duration": 30,
            "caption": f"caption {i}",
            "thumbnail_url": None,
            "indexed_at": base_iso,
        }
        for i in range(10)
    ]
    with patch("getviews_pipeline.supabase_client.get_service_client", return_value=MagicMock()):
        inner = build_generic_report(5, "broad query", window_days=14)
    p = GenericPayload.model_validate(inner)
    assert p.confidence.sample_size == 10
    assert p.confidence.intent_confidence == "low"
    assert p.confidence.niche_scope is None
    assert len(p.evidence_videos) == 3
    # Narrative must be ≤ 2 paragraphs, each ≤ 320 chars.
    paras = p.narrative.get("paragraphs", [])
    assert 1 <= len(paras) <= NARRATIVE_MAX_PARAGRAPHS
    for para in paras:
        assert len(para) <= NARRATIVE_PARAGRAPH_MAX_CHARS


def test_generic_envelope_validates_with_any_narrative_length_below_cap() -> None:
    inner = build_fixture_generic_report()
    # Short narrative is valid — the model allows 1..2 paragraphs.
    inner["narrative"] = {"paragraphs": ["Ngắn và gọn."]}
    p = GenericPayload.model_validate(inner)
    assert p.narrative["paragraphs"] == ["Ngắn và gọn."]
