"""Video diagnosis orchestration service (Phase 3.2).

Phase 1.1: thin re-export from video_analyze.py and pipelines.py.
Phase 3.2: owns run_video_diagnosis_core — the comparative narrative synthesis
           layer that runs on both on-demand and corpus paths via the shared
           boundary contract (DiagnosisInput → DiagnosisResult).

The two-core split:
  run_extraction_core   (services/extraction.py) → ExtractionResult
  run_video_diagnosis_core (this file)           → DiagnosisResult

Both take DiagnosisInput; run_video_diagnosis_core never calls Gemini
analyze_video — that is extraction-layer territory.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from getviews_pipeline.video_analyze import (  # noqa: F401
    finalize_video_narrative_layer,
    run_video_analyze_on_demand,
    run_video_analyze_pipeline,
)

__all__ = [
    "run_video_analyze_pipeline",
    "run_video_analyze_on_demand",
    "finalize_video_narrative_layer",
    "run_video_diagnosis_core",
]


def run_video_diagnosis_core(inp: "DiagnosisInput") -> "DiagnosisResult":  # noqa: F821
    """Shared diagnosis core — from ExtractionResult to DiagnosisResult.

    Accepts a fully-populated DiagnosisInput and runs:
      1. extract_video_errors (Gemini Call 1 — structured error list)
      2. apply_rule_based_video_errors (deterministic post-process)
      3. extract_hook_phases + decompose_segments (structural parse)
      4. model_retention_curve (curve modeling)

    Does NOT call synthesize_diagnosis_v2 / narrative synthesis — that is
    finalize_video_narrative_layer's responsibility (unchanged callers).

    Returns a DiagnosisResult that callers (on-demand pipeline, corpus ingest)
    can directly persist or pass to finalize_video_narrative_layer.

    Phase 3.3 will wire the 4 existing callers to this core.
    """
    from getviews_pipeline.models import DiagnosisInput, DiagnosisResult
    from getviews_pipeline.services.extraction import (
        apply_rule_based_video_errors,
        extract_video_errors,
    )
    from getviews_pipeline.video_analyze import (
        decompose_segments,
        extract_hook_phases,
    )
    from getviews_pipeline import telemetry

    assert isinstance(inp, DiagnosisInput), f"Expected DiagnosisInput, got {type(inp)}"

    if not inp.extraction.ok:
        logger.warning(
            "[diagnosis_core] extraction not ok for vid=%s: %s",
            inp.extraction.video_id,
            inp.extraction.error,
        )
        return DiagnosisResult(errors=[])

    analysis: dict[str, Any] = (
        inp.extraction.analysis.model_dump()
        if inp.extraction.analysis is not None
        else {}
    )
    video_row: dict[str, Any] = dict(inp.video_row)
    mode = inp.mode

    # ── Segments & hook cards ─────────────────────────────────────────────────
    with telemetry.span("diagnosis_core.structural_parse", video_id=inp.extraction.video_id):
        segments = decompose_segments(analysis)
        hook_cards = extract_hook_phases(analysis)
        # Strip body from hook cards (bandwidth savings for FE)
        for h in hook_cards:
            if isinstance(h, dict) and "body" in h:
                del h["body"]

    # ── Error extraction (Gemini Call 1) ──────────────────────────────────────
    with telemetry.span(
        "diagnosis_core.extract_errors",
        video_id=inp.extraction.video_id,
        mode=mode,
    ):
        retention_user = inp.retention_user or []
        raw_errors = extract_video_errors(
            extraction_mode=mode,
            video=video_row,
            analysis=analysis,
            niche_label=inp.niche_label or "unknown",
            niche_row=inp.niche_row,
            retention_curve=retention_user,
        )
        content_format_str = str(video_row.get("content_format") or inp.content_format or "")
        caption_hint = str(video_row.get("caption") or "").strip() or None

        from getviews_pipeline.video_analyze import video_duration_sec
        dur = video_duration_sec(analysis)

        errors = apply_rule_based_video_errors(
            raw_errors,
            analysis,
            content_format_str,
            caption_hint=caption_hint,
            duration_sec=float(dur) if dur > 0 else None,
        )

    return DiagnosisResult(
        errors=errors,
        hook_cards=hook_cards,
        segments=segments,
        retention_curve=retention_user,
        niche_benchmark_curve=inp.niche_benchmark or [],
    )
