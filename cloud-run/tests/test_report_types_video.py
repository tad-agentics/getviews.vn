"""PR-1 — ``video`` ReportV1 envelope.

Pre-requisite for PR-2 (VideoBody on /app/answer + /stream emit) +
PR-3 (drop /app/video screen). These tests pin the contract on the
type addition itself — the answer-session writer can store a
``{kind: "video", report: VideoAnalyzeResponse}`` envelope without
violating Pydantic validation, and the kind literal flows through
``validate_and_store_report``.

This PR ships dark — no /stream emit logic yet, no FE dispatch — so
these are the only behavioural tests. PR-2 will add end-to-end
tests once the emit + render path exists.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from getviews_pipeline.report_types import (
    ReportKind,
    ReportV1,
    VideoPayload,
    validate_and_store_report,
)


def _video_payload_fixture() -> dict[str, Any]:
    """Minimal but realistic VideoAnalyzeResponse-shaped dict.

    Mirrors the shape produced by ``run_video_analyze_pipeline`` /
    ``run_video_analyze_on_demand`` — those are the only emitters PR-2
    will wire into ``/stream``, so the test fixture follows the same
    keys they populate.
    """
    return {
        "video_id": "7630766288574369045",
        "mode": "win",
        "meta": {
            "creator": "creatorx",
            "views": 250_000,
            "likes": 18_000,
            "comments": 800,
            "shares": 1_200,
            "save_rate": 0.04,
            "duration_sec": 28.5,
            "thumbnail_url": "https://r2.test/thumbnails/7630766288574369045.png",
            "date_posted": "2026-04-15",
            "title": "Đây là cách",
            "niche_label": "Làm đẹp",
            "retention_source": "modeled",
        },
        "kpis": [
            {"label": "VIEW", "value": "250K", "delta": "2.5× kênh"},
            {"label": "GIỮ CHÂN", "value": "65%", "delta": "ngách TB"},
        ],
        "segments": [{"name": "hook", "pct": 0.1, "color_key": "accent"}],
        "hook_phases": [
            {"t_range": "0.0–0.8s", "label": "Hook đảo", "body": "Câu hỏi đảo neo attention."},
        ],
        "errors": [],
        "retention_curve": [{"t": 0.0, "pct": 100.0}, {"t": 1.0, "pct": 65.0}],
        "niche_benchmark_curve": [{"t": 0.0, "pct": 100.0}, {"t": 1.0, "pct": 55.0}],
        "niche_meta": {
            "avg_views": 100_000.0,
            "avg_retention": 0.55,
            "avg_ctr": 0.04,
            "sample_size": 200,
            "winners_sample_size": 30,
        },
    }


# ── Direct VideoPayload validation ──────────────────────────────────


def test_video_payload_accepts_full_corpus_shape() -> None:
    """The full corpus-row response shape passes Pydantic validation
    so the answer-session writer can store it as-is."""
    payload = _video_payload_fixture()
    out = VideoPayload.model_validate(payload)
    assert out.video_id == "7630766288574369045"
    assert out.mode == "win"
    assert out.meta.creator == "creatorx"
    assert out.niche_meta is not None
    assert out.niche_meta.winners_sample_size == 30


def test_video_payload_accepts_creator_comparison() -> None:
    payload = _video_payload_fixture()
    payload["creator_comparison"] = {
        "creator_handle": "@creatorx",
        "total_posts_analyzed": 12,
        "median_views": 50_000,
        "hit": {
            "video_id": "111",
            "tiktok_url": "https://www.tiktok.com/@creatorx/video/111",
            "views": 800_000,
            "hook_type": "Hook a",
            "thumbnail_url": "https://x.test/h.png",
        },
        "flop": {
            "video_id": "222",
            "tiktok_url": "https://www.tiktok.com/@creatorx/video/222",
            "views": 400,
            "hook_type": "Hook b",
            "thumbnail_url": None,
        },
        "delta": 2000,
        "target_vs_median": 5.0,
        "target_percentile": "top 10% kênh",
    }
    out = VideoPayload.model_validate(payload)
    assert out.creator_comparison is not None
    assert out.creator_comparison.delta == 2000


def test_video_payload_accepts_flop_with_errors() -> None:
    payload = _video_payload_fixture()
    payload["mode"] = "flop"
    payload["errors"] = [
        {"error_id": "e1", "sev": "high", "t": 0.0, "end": 2.0, "title": "Hook yếu", "detail": "...", "fix": "..."},
    ]
    payload["narrative_vi"] = {
        "headline_vi": "Một câu chẩn đoán flop.",
        "ket_luan_nhanh": "",
        "van_de_chinh": "",
        "loi_chinh_narrative": [],
        "dinh_huong_chien_luoc": "",
        "lessons": [],
    }
    out = VideoPayload.model_validate(payload)
    assert out.mode == "flop"
    assert isinstance(out.errors, list) and len(out.errors) == 1


def test_video_payload_accepts_on_demand_source_flag() -> None:
    """``run_video_analyze_on_demand`` tags the response with
    ``source: "on_demand"`` so the FE can show a "phân tích trực
    tiếp" hint. The model accepts either ``corpus``, ``on_demand``,
    or absent."""
    payload = _video_payload_fixture()
    payload["source"] = "on_demand"
    out = VideoPayload.model_validate(payload)
    assert out.source == "on_demand"


def test_video_payload_rejects_unknown_mode() -> None:
    """``mode`` is the discriminator that drives win-vs-flop UI on
    the FE — unknown values must fail loudly, not silently default."""
    payload = _video_payload_fixture()
    payload["mode"] = "neutral"
    with pytest.raises(ValidationError):
        VideoPayload.model_validate(payload)


def test_video_payload_allows_extra_fields() -> None:
    """Extra fields pass through (``extra="allow"``) so additions to
    /video/analyze response don't immediately break the answer
    pipeline. PR-2 can tighten when the contract stabilises."""
    payload = _video_payload_fixture()
    payload["future_field"] = {"some": "data"}
    out = VideoPayload.model_validate(payload)
    # Extras land on the model; we don't assert on them, just that
    # validation didn't reject the envelope.
    assert out.video_id == "7630766288574369045"


# ── ReportV1 envelope ───────────────────────────────────────────────


def test_report_v1_accepts_video_kind() -> None:
    """The ``ReportV1`` discriminated envelope routes ``kind="video"``
    to ``VideoPayload``. This is what the answer-session writer stores
    in ``answer_turns.payload`` (JSONB)."""
    payload = _video_payload_fixture()
    envelope = ReportV1.model_validate({"kind": "video", "report": payload})
    assert envelope.kind == "video"
    assert isinstance(envelope.report, VideoPayload)


def test_report_kind_literal_includes_video() -> None:
    """``ReportKind`` is the source-of-truth literal; FE mirror in
    ``api-types.ts`` must match."""
    # Literal types aren't iterable at runtime in the usual way;
    # introspect via __args__.
    assert "video" in ReportKind.__args__  # type: ignore[attr-defined]


# ── validate_and_store_report dispatch ──────────────────────────────


def test_validate_and_store_report_round_trips_video_envelope() -> None:
    """The JSONB-storage helper validates a ``video`` payload via
    VideoPayload and returns the envelope shape ``answer_turns.payload``
    expects."""
    payload = _video_payload_fixture()
    stored = validate_and_store_report("video", payload)
    assert stored == {"kind": "video", "report": payload}


def test_validate_and_store_report_rejects_video_with_bad_mode() -> None:
    """Mismatched payload + kind: ``kind="video"`` but report is
    missing ``video_id``. Must fail validation rather than store a
    half-formed envelope."""
    with pytest.raises(ValidationError):
        validate_and_store_report("video", {"mode": "win"})  # missing video_id, meta
