from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from getviews_pipeline.signals.base import Signal
from getviews_pipeline.signals.salience import SECTION_EMIT_THRESHOLD, section_emit_threshold

_CTX_SECTION_EMIT_THRESHOLD = "__section_emit_threshold"

# Diagnosis-first Sprint 2 §3: emit ``hook_analysis`` only when at least one hook
# signal in that section meets this bar (plan: type mismatch / contract / layering).
HOOK_ANALYSIS_SECTION_MIN_SALIENCE = 0.7

# §11 — emit ``persona`` when a persona-section signal reaches this bar.
PERSONA_SECTION_MIN_SALIENCE = 0.55


# §5 — emit ``editing`` when a signal meets this bar (plan salience down to 0.4).
EDITING_SECTION_MIN_SALIENCE = 0.4

# §8 — Douyin section includes 0.45 salience (trailing) — below default section gate.
DOUYIN_SECTION_MIN_SALIENCE = 0.45


class VideoSectionId(StrEnum):
    diagnosis = "diagnosis"
    compliance = "compliance"
    hook_analysis = "hook_analysis"
    niche_pattern = "niche_pattern"
    douyin_origin = "douyin_origin"
    channel_pattern = "channel_pattern"
    commerce = "commerce"
    metadata = "metadata"
    editing = "editing"
    sound = "sound"
    persona = "persona"
    script_structure = "script_structure"
    next_video = "next_video"
    boost_attribution = "boost_attribution"


Manifest = dict[str, list[Signal]]
AppliesFn = Callable[[dict, Manifest], bool]


@dataclass(frozen=True)
class SectionSpec:
    section_id: VideoSectionId
    display_order: int
    always_emit: bool
    applies: AppliesFn


def _emit_threshold_from_ctx(ctx: dict) -> float:
    raw = ctx.get(_CTX_SECTION_EMIT_THRESHOLD)
    if isinstance(raw, (int, float)):
        return float(raw)
    return SECTION_EMIT_THRESHOLD


def _has_gate(manifest: Manifest, section_id: str, ctx: dict) -> bool:
    threshold = _emit_threshold_from_ctx(ctx)
    return any(s.salience >= threshold for s in manifest.get(section_id, []))


def _applies_compliance(ctx: dict, manifest: Manifest) -> bool:
    if ctx.get("compliance_flags"):
        return True
    return bool(manifest.get("compliance"))


def _applies_niche_pattern(ctx: dict, _manifest: Manifest) -> bool:
    refs = ctx.get("reference_videos") or []
    return isinstance(refs, list) and len(refs) > 0


def _applies_douyin_origin(_ctx: dict, manifest: Manifest) -> bool:
    return any(
        s.salience >= DOUYIN_SECTION_MIN_SALIENCE
        for s in manifest.get("douyin_origin", [])
    )


def _applies_channel_pattern(ctx: dict, _manifest: Manifest) -> bool:
    ch = ctx.get("channel_context") or {}
    if not isinstance(ch, dict) or not ch.get("available"):
        return False
    n = int(ch.get("sample_size") or 0)
    # Live ED fallback has less signal per video (no content_format) — require ≥ 3 posts.
    # Corpus-backed context is richer, so 2 suffices for a meaningful comparison.
    min_n = 3 if ch.get("source") == "live" else 2
    return n >= min_n


def _applies_commerce(ctx: dict, manifest: Manifest) -> bool:
    """Emit commerce when extractors produced commerce signals OR legacy promo is non-organic.

    Organic + ``commerce_intent`` (e.g. shop_direct) still yields §0/§12 signals; the section
    must open whenever ``manifest[\"commerce\"]`` is non-empty, otherwise v6 drops the manifest.

    Fallback: business/brand account_type always warrants a commerce section even when
    Gemini classifies the video as organic (brand showcase without explicit shop CTA).
    """
    if manifest.get("commerce"):
        return True
    ua = ctx.get("user_analysis") or {}
    promo = str(ua.get("promotion_type") or "organic").lower()
    if promo not in ("organic", ""):
        return True
    us = ctx.get("user_stats") or {}
    account_type = str(us.get("account_type") or "").lower()
    return account_type in ("business", "brand", "creator_marketplace")


def _has_metadata_context(ctx: dict) -> bool:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return False
    enr = ua.get("enrichment")
    if isinstance(enr, dict):
        if str(enr.get("target_audience") or "").strip():
            return True
        if str(enr.get("tone") or "").strip():
            return True
        pains = enr.get("pain_points")
        if isinstance(pains, list) and any(str(p).strip() for p in pains):
            return True
        tags = enr.get("style_tags")
        if isinstance(tags, list) and any(str(t).strip() for t in tags):
            return True
        promo = str(enr.get("promotion_type") or "organic").lower()
        if promo not in ("organic", ""):
            return True
    us = ctx.get("user_stats") or {}
    if isinstance(us, dict) and us.get("creator_median_views") not in (None, "", 0):
        return True
    sh = us.get("stats_history") if isinstance(us, dict) else None
    if isinstance(sh, list):
        valid = [
            item
            for item in sh
            if isinstance(item, dict)
            and item.get("phase")
            and isinstance(item.get("views"), (int, float))
        ]
        if len(valid) >= 2:
            return True
    return False


def _applies_metadata(ctx: dict, manifest: Manifest) -> bool:
    if _has_metadata_context(ctx):
        return True
    return _has_gate(manifest, "metadata", ctx)


def _applies_editing(_ctx: dict, manifest: Manifest) -> bool:
    return any(
        s.salience >= EDITING_SECTION_MIN_SALIENCE
        for s in manifest.get("editing", [])
    )


def _applies_persona(_ctx: dict, manifest: Manifest) -> bool:
    return any(
        s.salience >= PERSONA_SECTION_MIN_SALIENCE
        for s in manifest.get("persona", [])
    )


def _video_has_audible_sound_track(ctx: dict) -> bool:
    us = ctx.get("user_stats") or {}
    if str(us.get("sound_id") or "").strip():
        return True
    if str(us.get("music_title") or "").strip():
        return True
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return False
    role = str(ua.get("audio_track_role") or "").strip().lower()
    if role and role != "silent":
        return True
    transcript = str(ua.get("audio_transcript") or "").strip()
    if len(transcript) >= 20:
        return True
    tags = {str(t).strip().lower() for t in (ua.get("style_tags") or []) if t}
    if len(transcript) >= 8 and (
        "voiceover_only" in tags
        or "talking_head" in tags
        or ua.get("has_human_speaking_to_camera") is True
    ):
        return True
    return False


def _applies_sound(ctx: dict, manifest: Manifest) -> bool:
    if not _video_has_audible_sound_track(ctx):
        return False
    return _has_gate(manifest, "sound", ctx)


def _has_structural_arc(ctx: dict) -> bool:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return False
    if str(ua.get("content_arc") or "").strip():
        return True
    if str(ua.get("pacing") or "").strip():
        return True
    beats = ua.get("story_beats")
    return isinstance(beats, list) and len(beats) > 0


def _video_has_scene_timeline(ctx: dict) -> bool:
    """A real (non-carousel) video with a scene timeline always warrants a structure block.

    The structure section renders the segment breakdown + script prose even when no
    `script_structure` *signal* fired (e.g. a short mukbang has no affiliate-phase /
    livestream-funnel / zero-value-stretch gap). Carousels use ``slides`` not ``scenes``
    and get their own handling, so they are excluded.
    """
    fmt = str(ctx.get("content_format") or "").strip().lower()
    if "carousel" in fmt:
        return False
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return False
    if ua.get("slides"):
        return False
    scenes = ua.get("scenes")
    return isinstance(scenes, list) and len(scenes) >= 1


def _applies_script_structure(ctx: dict, manifest: Manifest) -> bool:
    if _has_structural_arc(ctx):
        return True
    if _video_has_scene_timeline(ctx):
        return True
    return _has_gate(manifest, "script_structure", ctx)


def _hook_analysis_min_salience(ctx: dict) -> float:
    return HOOK_ANALYSIS_SECTION_MIN_SALIENCE


def _applies_hook_analysis(ctx: dict, manifest: Manifest) -> bool:
    ua = ctx.get("user_analysis") or {}
    if isinstance(ua, dict):
        ha = ua.get("hook_analysis")
        if isinstance(ha, dict) and (
            str(ha.get("hook_type") or "").strip()
            or str(ha.get("hook_phrase") or "").strip()
            or str(ha.get("first_frame_type") or "").strip()
        ):
            return True
    min_sal = _hook_analysis_min_salience(ctx)
    return any(s.salience >= min_sal for s in manifest.get("hook_analysis", []))


def _applies_boost_attribution(ctx: dict, manifest: Manifest) -> bool:
    return _has_gate(manifest, "boost_attribution", ctx)


SECTION_POOL: tuple[SectionSpec, ...] = (
    SectionSpec(VideoSectionId.diagnosis, 10, True, lambda _c, _m: True),
    SectionSpec(VideoSectionId.compliance, 15, False, _applies_compliance),
    SectionSpec(VideoSectionId.hook_analysis, 20, False, _applies_hook_analysis),
    SectionSpec(VideoSectionId.niche_pattern, 40, False, _applies_niche_pattern),
    SectionSpec(VideoSectionId.douyin_origin, 45, False, _applies_douyin_origin),
    SectionSpec(VideoSectionId.channel_pattern, 50, False, _applies_channel_pattern),
    SectionSpec(VideoSectionId.commerce, 60, False, _applies_commerce),
    SectionSpec(VideoSectionId.metadata, 58, False, _applies_metadata),
    SectionSpec(VideoSectionId.editing, 59, False, _applies_editing),
    SectionSpec(VideoSectionId.sound, 62, False, _applies_sound),
    SectionSpec(VideoSectionId.persona, 65, False, _applies_persona),
    SectionSpec(VideoSectionId.script_structure, 68, False, _applies_script_structure),
    SectionSpec(VideoSectionId.boost_attribution, 70, False, _applies_boost_attribution),
    SectionSpec(VideoSectionId.next_video, 90, True, lambda _c, _m: True),
)


VIDEO_SECTION_DEFAULT_TITLES: dict[tuple[str, str], str] = {
    ("diagnosis", "hit"): "Đang làm tốt",
    ("diagnosis", "average"): "Điểm mạnh và khoảng trống",
    ("diagnosis", "flop"): "Vấn đề chính",
    ("diagnosis", "unknown"): "Bức tranh phân tích",
    ("compliance", "hit"): "Vi phạm chính sách",
    ("compliance", "average"): "Vi phạm chính sách",
    ("compliance", "flop"): "Vi phạm chính sách",
    ("compliance", "unknown"): "Vi phạm chính sách",
    ("hook_analysis", "hit"): "Phân tích hook",
    ("hook_analysis", "average"): "Phân tích hook",
    ("hook_analysis", "flop"): "Phân tích hook",
    ("hook_analysis", "unknown"): "Phân tích hook",
    ("niche_pattern", "hit"): "Công thức đang chạy trong ngách",
    ("niche_pattern", "average"): "Công thức đang chạy trong ngách",
    ("niche_pattern", "flop"): "Công thức đang chạy trong ngách",
    ("niche_pattern", "unknown"): "Công thức đang chạy trong ngách",
    ("douyin_origin", "hit"): "Nguồn gốc Douyin",
    ("douyin_origin", "average"): "Nguồn gốc Douyin",
    ("douyin_origin", "flop"): "Nguồn gốc Douyin",
    ("douyin_origin", "unknown"): "Nguồn gốc Douyin",
    ("channel_pattern", "hit"): "Video này so với kênh bạn",
    ("channel_pattern", "average"): "Video này so với kênh bạn",
    ("channel_pattern", "flop"): "Video này so với kênh bạn",
    ("channel_pattern", "unknown"): "Video này so với kênh bạn",
    ("commerce", "hit"): "Kêu gọi hành động",
    ("commerce", "average"): "Kêu gọi hành động",
    ("commerce", "flop"): "Kêu gọi hành động",
    ("commerce", "unknown"): "Kêu gọi hành động",
    ("metadata", "hit"): "Phân tích bối cảnh & diễn biến",
    ("metadata", "average"): "Phân tích bối cảnh & diễn biến",
    ("metadata", "flop"): "Phân tích bối cảnh & diễn biến",
    ("metadata", "unknown"): "Phân tích bối cảnh & diễn biến",
    ("editing", "hit"): "Màu sắc và chữ trên hình",
    ("editing", "average"): "Màu sắc và chữ trên hình",
    ("editing", "flop"): "Màu sắc và chữ trên hình",
    ("editing", "unknown"): "Màu sắc và chữ trên hình",
    ("sound", "hit"): "Âm thanh và nhịp điệu",
    ("sound", "average"): "Âm thanh và nhịp điệu",
    ("sound", "flop"): "Âm thanh và nhịp điệu",
    ("sound", "unknown"): "Âm thanh và nhịp điệu",
    ("persona", "hit"): "Phong cách và nhân vật",
    ("persona", "average"): "Phong cách và nhân vật",
    ("persona", "flop"): "Phong cách và nhân vật",
    ("persona", "unknown"): "Phong cách và nhân vật",
    ("script_structure", "hit"): "Phân tích cấu trúc Video",
    ("script_structure", "average"): "Phân tích cấu trúc Video",
    ("script_structure", "flop"): "Phân tích cấu trúc Video",
    ("script_structure", "unknown"): "Phân tích cấu trúc Video",
    ("boost_attribution", "hit"): "Có dấu hiệu ads/seeding",
    ("boost_attribution", "average"): "Có dấu hiệu ads/seeding",
    ("boost_attribution", "flop"): "Có dấu hiệu ads/seeding",
    ("boost_attribution", "unknown"): "Có dấu hiệu ads/seeding",
    ("next_video", "hit"): "Video tiếp theo nên quay",
    ("next_video", "average"): "Video tiếp theo nên quay",
    ("next_video", "flop"): "Video tiếp theo nên quay",
    ("next_video", "unknown"): "Video tiếp theo nên quay",
}


def default_section_title(section_id: str, performance_tier: str) -> str:
    tier = str(performance_tier or "unknown").lower()
    if tier == "early":
        # Age-inconclusive — neutral (average) titles, never the flop set.
        tier = "average"
    if tier not in ("hit", "average", "flop", "unknown"):
        tier = "unknown"
    return VIDEO_SECTION_DEFAULT_TITLES.get(
        (section_id, tier),
        VIDEO_SECTION_DEFAULT_TITLES.get((section_id, "unknown"), section_id.upper()),
    )


# Redesign 2026-05: actionable blocks first; cap deep narrative sections.
_REDESIGN_PRIORITY_ORDER: tuple[str, ...] = (
    "diagnosis",
    "compliance",
    "hook_analysis",
    "niche_pattern",
    "next_video",
)
DEEP_SECTION_CAP = 7

# Core "anatomy" sections that must survive the cap even when context sections
# (channel/commerce/boost) carry higher signal salience. After basic/deep tiers
# were removed (2026-06-11) a paid report is a single "full" report — the video
# structure breakdown is part of that promise, not a salience-negotiable extra.
# These count toward the cap (they displace the weakest contested section) but
# keep their natural display-order position.
_RESERVED_ANATOMY: tuple[str, ...] = ("script_structure", "editing", "sound", "persona")


def _section_display_order() -> dict[str, int]:
    return {spec.section_id.value: spec.display_order for spec in SECTION_POOL}


def _reorder_and_cap_sections(
    sections: list[str],
    *,
    manifest: Manifest | None = None,
) -> list[str]:
    """Put diagnosis → niche_pattern → next_video first; cap deep at DEEP_SECTION_CAP.

    2026-06-11 salience audit: when the cap bites, non-priority slots are won
    by each section's strongest signal (max salience), not by static display
    order — a 0.9-salience persona section no longer loses to a barely-gated
    0.5 metadata section. Survivors still render in display order.

    2026-06-13: ``_RESERVED_ANATOMY`` sections are protected from the cap — they
    keep their display slot and displace the lowest-salience contested section
    instead of being dropped (a mukbang's structure block was lost to
    channel/commerce/boost despite being core to the report).
    """
    pri = [s for s in _REDESIGN_PRIORITY_ORDER if s in sections]
    rest = [s for s in sections if s not in _REDESIGN_PRIORITY_ORDER]
    order_map = _section_display_order()
    rest.sort(key=lambda s: order_map.get(s, 999))
    out = pri + rest
    if len(out) <= DEEP_SECTION_CAP:
        return out
    pri_set = frozenset(_REDESIGN_PRIORITY_ORDER)
    reserved_set = frozenset(_RESERVED_ANATOMY)
    priority = [s for s in out if s in pri_set]
    reserved = [s for s in out if s in reserved_set]
    contested = [s for s in out if s not in pri_set and s not in reserved_set]
    slots = max(0, DEEP_SECTION_CAP - len(priority) - len(reserved))
    if manifest is not None and slots < len(contested):

        def _max_salience(sid: str) -> float:
            return max((s.salience for s in manifest.get(sid, [])), default=0.0)

        keep = set(
            sorted(
                contested, key=lambda sid: (-_max_salience(sid), order_map.get(sid, 999))
            )[:slots]
        )
        contested = [s for s in contested if s in keep]
    else:
        contested = contested[:slots]
    # Reserved anatomy rejoins the non-priority tail in display order.
    tail = sorted(reserved + contested, key=lambda s: order_map.get(s, 999))
    return priority + tail


def _select_sections_full(manifest: Manifest, ctx: dict) -> list[str]:
    """Salience pool selection (pre-depth filter)."""
    out: list[str] = []
    seen: set[str] = set()
    for spec in sorted(SECTION_POOL, key=lambda s: s.display_order):
        ok = spec.applies(ctx, manifest) if not spec.always_emit else True
        if not ok:
            continue
        sid = spec.section_id.value
        if sid in seen:
            continue
        seen.add(sid)
        out.append(sid)

    # Compliance immediately after diagnosis when both present
    if "compliance" in out and "diagnosis" in out:
        out = [s for s in out if s not in ("diagnosis", "compliance")]
        idx_diag = 0
        out.insert(idx_diag, "diagnosis")
        out.insert(idx_diag + 1, "compliance")
    return out


def _ctx_with_emit_threshold(ctx: dict) -> dict:
    gated = dict(ctx)
    gated[_CTX_SECTION_EMIT_THRESHOLD] = section_emit_threshold()
    return gated


def select_sections_to_emit(
    manifest: Manifest,
    ctx: dict,
) -> list[str]:
    """Return section_id strings in display order (compliance forced after diagnosis)."""
    full = _select_sections_full(manifest, _ctx_with_emit_threshold(ctx))
    return _reorder_and_cap_sections(full, manifest=manifest)


def section_ids_ordered() -> list[str]:
    return [s.section_id.value for s in sorted(SECTION_POOL, key=lambda x: x.display_order)]
