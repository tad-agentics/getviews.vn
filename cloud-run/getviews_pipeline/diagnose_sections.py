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


# §5 — emit ``editing`` when a signal meets this bar (plan salience down to 0.4).
EDITING_SECTION_MIN_SALIENCE = 0.4

# §8 — Douyin section includes 0.45 salience (trailing) — below default section gate.
DOUYIN_SECTION_MIN_SALIENCE = 0.45


class VideoSectionId(StrEnum):
    diagnosis = "diagnosis"
    compliance = "compliance"
    hook_analysis = "hook_analysis"
    distribution = "distribution"
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


def _applies_metadata(_ctx: dict, manifest: Manifest) -> bool:
    return _has_gate(manifest, "metadata")


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
    return False


def _applies_sound(ctx: dict, manifest: Manifest) -> bool:
    if not _video_has_audible_sound_track(ctx):
        return False
    return _has_gate(manifest, "sound")


def _applies_script_structure(_ctx: dict, manifest: Manifest) -> bool:
    return _has_gate(manifest, "script_structure")


def _applies_hook_analysis(_ctx: dict, manifest: Manifest) -> bool:
    return any(
        s.salience >= HOOK_ANALYSIS_SECTION_MIN_SALIENCE
        for s in manifest.get("hook_analysis", [])
    )


def _applies_boost_attribution(_ctx: dict, manifest: Manifest) -> bool:
    return _has_gate(manifest, "boost_attribution")


SECTION_POOL: tuple[SectionSpec, ...] = (
    SectionSpec(VideoSectionId.diagnosis, 10, True, lambda _c, _m: True),
    SectionSpec(VideoSectionId.compliance, 15, False, _applies_compliance),
    SectionSpec(VideoSectionId.hook_analysis, 20, False, _applies_hook_analysis),
    SectionSpec(VideoSectionId.distribution, 30, False, _applies_distribution),
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
    ("douyin_origin", "hit"): "NGUỒN GỐC DOUYIN",
    ("douyin_origin", "average"): "NGUỒN GỐC DOUYIN",
    ("douyin_origin", "flop"): "NGUỒN GỐC DOUYIN",
    ("douyin_origin", "unknown"): "NGUỒN GỐC DOUYIN",
    ("channel_pattern", "hit"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("channel_pattern", "average"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("channel_pattern", "flop"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("channel_pattern", "unknown"): "VIDEO NÀY SO VỚI KÊNH BẠN",
    ("commerce", "hit"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("commerce", "average"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("commerce", "flop"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("commerce", "unknown"): "THƯƠNG MẠI VÀ CHUYỂN ĐỔI",
    ("metadata", "hit"): "KHUNG AN TOÀN VÀ LOẠI TÀI KHOẢN",
    ("metadata", "average"): "KHUNG AN TOÀN VÀ LOẠI TÀI KHOẢN",
    ("metadata", "flop"): "KHUNG AN TOÀN VÀ LOẠI TÀI KHOẢN",
    ("metadata", "unknown"): "KHUNG AN TOÀN VÀ LOẠI TÀI KHOẢN",
    ("editing", "hit"): "MÀU SẮC VÀ CHỮ TRÊN HÌNH",
    ("editing", "average"): "MÀU SẮC VÀ CHỮ TRÊN HÌNH",
    ("editing", "flop"): "MÀU SẮC VÀ CHỮ TRÊN HÌNH",
    ("editing", "unknown"): "MÀU SẮC VÀ CHỮ TRÊN HÌNH",
    ("sound", "hit"): "ÂM THANH VÀ NHỊP ĐIỆU",
    ("sound", "average"): "ÂM THANH VÀ NHỊP ĐIỆU",
    ("sound", "flop"): "ÂM THANH VÀ NHỊP ĐIỆU",
    ("sound", "unknown"): "ÂM THANH VÀ NHỊP ĐIỆU",
    ("persona", "hit"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("persona", "average"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("persona", "flop"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("persona", "unknown"): "PHONG CÁCH VÀ NHÂN VẬT",
    ("script_structure", "hit"): "CẤU TRÚC KỊCH BẢN",
    ("script_structure", "average"): "CẤU TRÚC KỊCH BẢN",
    ("script_structure", "flop"): "CẤU TRÚC KỊCH BẢN",
    ("script_structure", "unknown"): "CẤU TRÚC KỊCH BẢN",
    ("boost_attribution", "hit"): "CÓ DẤU HIỆU ADS/SEEDING",
    ("boost_attribution", "average"): "CÓ DẤU HIỆU ADS/SEEDING",
    ("boost_attribution", "flop"): "CÓ DẤU HIỆU ADS/SEEDING",
    ("boost_attribution", "unknown"): "CÓ DẤU HIỆU ADS/SEEDING",
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


# §4.2 — basic depth whitelist (Win + Flop share the same set).
BASIC_SECTION_ALLOWLIST = frozenset({
    "diagnosis",
    "compliance",
    "hook_analysis",
    "niche_pattern",
    "next_video",
})


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


def select_sections_to_emit(
    manifest: Manifest,
    ctx: dict,
    *,
    depth: str = "basic",
) -> list[str]:
    """Return section_id strings in display order (compliance forced after diagnosis).

    ``depth=basic`` applies §4.2 whitelist; ``depth=deep`` keeps full salience pool.
    Default ``basic`` matches Answer-session product default (explicit ``deep`` when billed 2×).
    """
    full = _select_sections_full(manifest, ctx)
    if depth == "basic":
        return [s for s in full if s in BASIC_SECTION_ALLOWLIST]
    return full


def section_ids_ordered() -> list[str]:
    return [s.section_id.value for s in sorted(SECTION_POOL, key=lambda x: x.display_order)]
