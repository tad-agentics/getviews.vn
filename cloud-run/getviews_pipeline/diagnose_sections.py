from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from getviews_pipeline.signals.base import Signal
from getviews_pipeline.signals.salience import SECTION_EMIT_THRESHOLD

# Diagnosis-first Sprint 2 §3: emit ``hook_analysis`` only when at least one hook
# signal in that section meets this bar (plan: type mismatch / contract / layering).
HOOK_ANALYSIS_SECTION_MIN_SALIENCE = 0.7

# §11 — emit ``persona`` when a persona-section signal reaches this bar.
PERSONA_SECTION_MIN_SALIENCE = 0.55


class VideoSectionId(StrEnum):
    diagnosis = "diagnosis"
    compliance = "compliance"
    hook_analysis = "hook_analysis"
    distribution = "distribution"
    niche_pattern = "niche_pattern"
    channel_pattern = "channel_pattern"
    commerce = "commerce"
    persona = "persona"
    next_video = "next_video"


Manifest = dict[str, list[Signal]]
AppliesFn = Callable[[dict, Manifest], bool]


@dataclass(frozen=True)
class SectionSpec:
    section_id: VideoSectionId
    display_order: int
    always_emit: bool
    applies: AppliesFn


def _has_gate(manifest: Manifest, section_id: str) -> bool:
    return any(s.salience >= SECTION_EMIT_THRESHOLD for s in manifest.get(section_id, []))


def _applies_compliance(ctx: dict, manifest: Manifest) -> bool:
    if ctx.get("compliance_flags"):
        return True
    return bool(manifest.get("compliance"))


def _applies_distribution(_ctx: dict, manifest: Manifest) -> bool:
    return _has_gate(manifest, "distribution")


def _applies_niche_pattern(ctx: dict, _manifest: Manifest) -> bool:
    refs = ctx.get("reference_videos") or []
    return isinstance(refs, list) and len(refs) > 0


def _applies_channel_pattern(ctx: dict, _manifest: Manifest) -> bool:
    ch = ctx.get("channel_context") or {}
    if not isinstance(ch, dict) or not ch.get("available"):
        return False
    return int(ch.get("sample_size") or 0) >= 3


def _applies_commerce(ctx: dict, _manifest: Manifest) -> bool:
    ua = ctx.get("user_analysis") or {}
    promo = str(ua.get("promotion_type") or "organic").lower()
    return promo not in ("organic", "")


def _applies_persona(_ctx: dict, manifest: Manifest) -> bool:
    return any(
        s.salience >= PERSONA_SECTION_MIN_SALIENCE
        for s in manifest.get("persona", [])
    )


def _applies_hook_analysis(_ctx: dict, manifest: Manifest) -> bool:
    return any(
        s.salience >= HOOK_ANALYSIS_SECTION_MIN_SALIENCE
        for s in manifest.get("hook_analysis", [])
    )


SECTION_POOL: tuple[SectionSpec, ...] = (
    SectionSpec(VideoSectionId.diagnosis, 10, True, lambda _c, _m: True),
    SectionSpec(VideoSectionId.compliance, 15, False, _applies_compliance),
    SectionSpec(VideoSectionId.hook_analysis, 20, False, _applies_hook_analysis),
    SectionSpec(VideoSectionId.distribution, 30, False, _applies_distribution),
    SectionSpec(VideoSectionId.niche_pattern, 40, False, _applies_niche_pattern),
    SectionSpec(VideoSectionId.channel_pattern, 50, False, _applies_channel_pattern),
    SectionSpec(VideoSectionId.commerce, 60, False, _applies_commerce),
    SectionSpec(VideoSectionId.persona, 65, False, _applies_persona),
    SectionSpec(VideoSectionId.next_video, 90, True, lambda _c, _m: True),
)


VIDEO_SECTION_DEFAULT_TITLES: dict[tuple[str, str], str] = {
    ("diagnosis", "hit"): "CƠ CHẾ CHẠY ĐÚNG",
    ("diagnosis", "average"): "ĐIỂM MẠNH VÀ KHOẢNG TRỐNG",
    ("diagnosis", "flop"): "VẤN ĐỀ CHÍNH",
    ("diagnosis", "unknown"): "BỨC TRANH PHÂN TÍCH",
    ("compliance", "hit"): "RỦI RO PHÁP LÝ",
    ("compliance", "average"): "RỦI RO PHÁP LÝ",
    ("compliance", "flop"): "RỦI RO PHÁP LÝ",
    ("compliance", "unknown"): "RỦI RO PHÁP LÝ",
    ("hook_analysis", "hit"): "PHÂN TÍCH HOOK",
    ("hook_analysis", "average"): "PHÂN TÍCH HOOK",
    ("hook_analysis", "flop"): "PHÂN TÍCH HOOK",
    ("hook_analysis", "unknown"): "PHÂN TÍCH HOOK",
    ("distribution", "hit"): "PHÂN PHỐI VÀ KHÁM PHÁ",
    ("distribution", "average"): "PHÂN PHỐI VÀ KHÁM PHÁ",
    ("distribution", "flop"): "PHÂN PHỐI VÀ KHÁM PHÁ",
    ("distribution", "unknown"): "PHÂN PHỐI VÀ KHÁM PHÁ",
    ("niche_pattern", "hit"): "CÔNG THỨC ĐANG CHẠY TRONG NGÁCH",
    ("niche_pattern", "average"): "CÔNG THỨC ĐANG CHẠY TRONG NGÁCH",
    ("niche_pattern", "flop"): "CÔNG THỨC ĐANG CHẠY TRONG NGÁCH",
    ("niche_pattern", "unknown"): "CÔNG THỨC ĐANG CHẠY TRONG NGÁCH",
    ("channel_pattern", "hit"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("channel_pattern", "average"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("channel_pattern", "flop"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("channel_pattern", "unknown"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("commerce", "hit"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("commerce", "average"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("commerce", "flop"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("commerce", "unknown"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("persona", "hit"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("persona", "average"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("persona", "flop"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("persona", "unknown"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("next_video", "hit"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "average"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "flop"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "unknown"): "VIDEO TIẾP THEO NÊN QUAY",
}


def default_section_title(section_id: str, performance_tier: str) -> str:
    tier = str(performance_tier or "unknown").lower()
    if tier not in ("hit", "average", "flop", "unknown"):
        tier = "unknown"
    return VIDEO_SECTION_DEFAULT_TITLES.get(
        (section_id, tier),
        VIDEO_SECTION_DEFAULT_TITLES.get((section_id, "unknown"), section_id.upper()),
    )


def select_sections_to_emit(manifest: Manifest, ctx: dict) -> list[str]:
    """Return section_id strings in display order (compliance forced after diagnosis)."""
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


def section_ids_ordered() -> list[str]:
    return [s.section_id.value for s in sorted(SECTION_POOL, key=lambda x: x.display_order)]
