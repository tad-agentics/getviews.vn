"""Salience-gated signal extractors for video diagnosis (diagnosis-first plan)."""

from getviews_pipeline.signals.registry import (
    build_diagnosis_ctx,
    build_signal_manifest,
    ensure_diagnosis_signals,
    manifest_for_prompt,
)

__all__ = [
    "build_diagnosis_ctx",
    "build_signal_manifest",
    "ensure_diagnosis_signals",
    "manifest_for_prompt",
]
