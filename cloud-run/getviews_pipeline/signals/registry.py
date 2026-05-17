from __future__ import annotations

from collections import defaultdict

from getviews_pipeline.signals.base import Evidence, Signal
from getviews_pipeline.signals.channel import extract_channel_signals
from getviews_pipeline.signals.commerce import extract_commerce_signals
from getviews_pipeline.signals.compliance import extract_compliance_signals
from getviews_pipeline.signals.context_signals import extract_context_signals
from getviews_pipeline.signals.distribution import extract_distribution_signals
from getviews_pipeline.signals.engagement import extract_engagement_signals
from getviews_pipeline.signals.hook import extract_hook_signals
from getviews_pipeline.signals.persona import extract_persona_signals
from getviews_pipeline.signals.reference import extract_reference_signals
from getviews_pipeline.signals.salience import MAX_SIGNALS_PER_SECTION_IN_PROMPT

_EXTRACTORS = (
    extract_compliance_signals,
    extract_distribution_signals,
    extract_engagement_signals,
    extract_context_signals,
    extract_hook_signals,
    extract_reference_signals,
    extract_channel_signals,
    extract_commerce_signals,
    extract_persona_signals,
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
) -> dict:
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
    }


def build_signal_manifest(ctx: dict) -> dict[str, list[Signal]]:
    manifest: dict[str, list[Signal]] = defaultdict(list)
    for ex in _EXTRACTORS:
        for sig in ex(ctx):
            manifest[sig.section_id].append(sig)

    for sid in manifest:
        manifest[sid].sort(key=lambda s: -s.salience)

    ensure_diagnosis_signals(manifest, ctx)
    if "diagnosis" in manifest:
        manifest["diagnosis"].sort(key=lambda s: -s.salience)

    return dict(manifest)


def manifest_for_prompt(
    manifest: dict[str, list[Signal]],
) -> dict[str, list[Signal]]:
    """Top-N signals per section for LLM payload only."""
    return {
        sid: lst[:MAX_SIGNALS_PER_SECTION_IN_PROMPT]
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
