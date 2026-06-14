from __future__ import annotations

import json
import logging
from collections import defaultdict

from getviews_pipeline.signals.base import Evidence, Signal
from getviews_pipeline.signals.channel import extract_channel_signals
from getviews_pipeline.signals.commerce import extract_commerce_signals
from getviews_pipeline.signals.compliance import extract_compliance_signals
from getviews_pipeline.signals.context_signals import extract_context_signals
from getviews_pipeline.signals.distribution import (
    extract_distribution_signals,
    extract_live_boost_attribution_signals,
)
from getviews_pipeline.signals.douyin import extract_douyin_signals
from getviews_pipeline.signals.editing import extract_editing_signals
from getviews_pipeline.signals.engagement import extract_engagement_signals
from getviews_pipeline.signals.hook import extract_hook_signals
from getviews_pipeline.signals.metadata import extract_metadata_signals
from getviews_pipeline.signals.performance import extract_commerce_performance_override_signal
from getviews_pipeline.signals.persona import extract_persona_signals
from getviews_pipeline.signals.reference import extract_reference_signals
from getviews_pipeline.signals.salience import (
    MAX_SIGNALS_PER_SECTION_DEEP,
)
from getviews_pipeline.signals.script import extract_script_signals
from getviews_pipeline.signals.sound import extract_sound_signals
from getviews_pipeline.signals.triggers import extract_trigger_signals
from getviews_pipeline.signals.win import extract_win_signals

logger = logging.getLogger(__name__)

_EXTRACTORS = (
    extract_compliance_signals,
    extract_distribution_signals,
    extract_live_boost_attribution_signals,
    extract_engagement_signals,
    extract_context_signals,
    extract_hook_signals,
    extract_reference_signals,
    extract_channel_signals,
    extract_commerce_signals,
    extract_commerce_performance_override_signal,
    extract_metadata_signals,
    extract_editing_signals,
    extract_douyin_signals,
    extract_sound_signals,
    extract_persona_signals,
    extract_script_signals,
    extract_trigger_signals,
    extract_win_signals,
)


def build_diagnosis_ctx(
    *,
    user_analysis: dict,
    user_stats: dict,
    reference_videos: list[dict],
    channel_context: dict | None,
    performance_tier: str,
    niche_meta: dict | None = None,
    compliance_flags: list[dict] | None = None,
    content_format: str = "",
    niche_name: str = "",
    corpus_size: int = 0,
    comment_radar: dict | None = None,
    hook_effectiveness: list[dict] | None = None,
    content_class_id: int | None = None,
) -> dict:
    cc_id = content_class_id
    if cc_id is None and isinstance(niche_meta, dict):
        raw = niche_meta.get("content_class_id")
        if raw is not None:
            try:
                cc_id = int(raw)
            except (TypeError, ValueError):
                cc_id = None
    return {
        "user_analysis": user_analysis,
        "user_stats": user_stats,
        "reference_videos": reference_videos,
        "channel_context": channel_context,
        "performance_tier": performance_tier,
        "niche_meta": niche_meta or {},
        "compliance_flags": list(compliance_flags or []),
        "content_format": content_format,
        "niche_name": niche_name,
        "corpus_size": corpus_size,
        "comment_radar": comment_radar if isinstance(comment_radar, dict) else None,
        "hook_effectiveness": list(hook_effectiveness or []),
        "content_class_id": cc_id,
    }


def build_signal_manifest(ctx: dict) -> dict[str, list[Signal]]:
    from getviews_pipeline.signal_calibration import signal_salience_multiplier

    content_class_id = ctx.get("content_class_id")
    cc_id = int(content_class_id) if content_class_id is not None else None

    manifest: dict[str, list[Signal]] = defaultdict(list)
    for ex in _EXTRACTORS:
        for sig in ex(ctx):
            multiplier = signal_salience_multiplier(sig.id, cc_id)
            if multiplier != 1.0:
                sig.salience = round(sig.salience * multiplier, 4)
            manifest[sig.section_id].append(sig)

    for sid in manifest:
        manifest[sid].sort(key=lambda s: -s.salience)

    ensure_diagnosis_signals(manifest, ctx)
    if "diagnosis" in manifest:
        manifest["diagnosis"].sort(key=lambda s: -s.salience)

    return dict(manifest)


def manifest_telemetry(
    manifest: dict[str, list[Signal]],
    *,
    sections_to_emit: list[str] | None = None,
) -> dict:
    """Summarize fired signals + section emit coverage for ops / ablation (Wave 2 B)."""
    signal_ids: list[str] = []
    sections_with_signals: dict[str, int] = {}
    for sid, signals in manifest.items():
        sections_with_signals[sid] = len(signals)
        signal_ids.extend(sig.id for sig in signals)

    out: dict = {
        "signal_count": len(signal_ids),
        "signal_ids": signal_ids,
        "sections_with_signals": sections_with_signals,
    }
    if sections_to_emit is not None:
        out["sections_to_emit"] = sections_to_emit
        out["sections_empty"] = [
            sid for sid in sections_to_emit if not manifest.get(sid)
        ]
    return out


def log_manifest_telemetry(
    telemetry: dict,
    *,
    depth: str,
    video_id: str | None = None,
) -> None:
    """Structured log line for Cloud Run log-based metrics (signal fire-rate sampling)."""
    payload: dict = {
        "event": "diagnosis_manifest_telemetry",
        "depth": depth,
        **telemetry,
    }
    if video_id:
        payload["video_id"] = video_id
    logger.info("%s", json.dumps(payload, ensure_ascii=False))


def manifest_for_prompt(
    manifest: dict[str, list[Signal]],
) -> dict[str, list[Signal]]:
    """Top-N signals per section for LLM payload only (§4.8 — cap 5)."""
    cap = MAX_SIGNALS_PER_SECTION_DEEP
    return {
        sid: lst[:cap]
        for sid, lst in manifest.items()
    }


def ensure_diagnosis_signals(manifest: dict[str, list[Signal]], ctx: dict) -> None:
    """Always surface at least one diagnosis finding so the lede has hooks."""
    if manifest.get("diagnosis"):
        return
    tier = str(ctx.get("performance_tier") or "unknown")
    manifest.setdefault("diagnosis", []).append(
        Signal(
            id="diagnosis_baseline",
            section_id="diagnosis",
            taxonomy_ref="§core",
            salience=0.55,
            claim=f"Mở bài chẩn đoán theo tier {tier} — tổng hợp hook, phân phối và baseline khi có dữ liệu.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"performance_tier={tier}",
                    location="ctx.performance_tier",
                )
            ],
            suggested_fix=None,
        )
    )
