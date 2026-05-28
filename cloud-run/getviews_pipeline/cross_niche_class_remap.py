"""Cross-niche content_class realignment after HI-11 in-niche route.

When Gemini ``niche_classification`` disagrees with the ingest loop's
``content_class_id`` (e.g. baby vlog filed under real_estate_listing because
HI-11 maps ``format_axis`` inside the loop niche), re-align ``content_class_id``
and optionally ``creator_niche_slug`` to the junction for the inferred topic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from getviews_pipeline.fashion_commerce_niche_remap import _analysis_signal_haystack
from getviews_pipeline.junction_content_class import (
    content_class_id_for_creator_niche_format,
    primary_creator_niche_id_for_content_class,
)
from getviews_pipeline.profile_niches import CREATOR_NICHE_SLUG_TO_ID
from getviews_pipeline.two_axis_taxonomy import junction_has_pair

logger = logging.getLogger(__name__)

_GEMINI_NICHE_CONFIDENCE_FLOOR = 0.6

# Loops that commonly swallow cross-topic viral clips (HI-11 in-niche route).
_MISFILE_LOOP_CREATOR_NICHE_IDS: frozenset[int] = frozenset({9, 16})  # business, real_estate

_BABY_FAMILY_RE = re.compile(
    r"(?:"
    r"em\s*b[eé]|baby|cục\s*cưng|funny\s*baby|gội\s*đầu|goi\s*dau|"
    r"mẹ\s*bỉm|me\s*bim|nuôi\s*con|sơ\s*sinh|so\s*sinh|"
    r"#baby|#cute|#funnybaby"
    r")",
    re.IGNORECASE,
)

_REAL_ESTATE_STRONG_RE = re.compile(
    r"(?:"
    r"bất\s*động\s*sản|bat\s*dong\s*san|nhà\s*đất|nha\s*dat|căn\s*hộ|can\s*ho|"
    r"m²|m2\b|triệu\s*/\s*m2|sổ\s*đỏ|so\s*do|listing|môi\s*giới\s*bđs|"
    r"đất\s*nền|dat\s*nen|cho\s*thuê\s*căn|ban\s*nha"
    r")",
    re.IGNORECASE,
)

_NICHE_SIGNAL_RES: dict[str, re.Pattern[str]] = {
    "family": re.compile(
        r"(?:em\s*b[eé]|baby|cục\s*cưng|gội\s*đầu|mẹ\s*bỉm|nuôi\s*con|#baby)",
        re.IGNORECASE,
    ),
    "food": re.compile(
        r"(?:ăn\s|mukbang|nấu\s|nau\s|ẩm\s*thực|am\s*thuc|quán\s|mon\s|recipe|công\s*thức)",
        re.IGNORECASE,
    ),
    "fashion": re.compile(
        r"(?:quần\s*áo|thời\s*trang|outfit|ootd|phụ\s*kiện|váy|lookbook|phối\s*đồ)",
        re.IGNORECASE,
    ),
    "beauty": re.compile(
        r"(?:skincare|makeup|mỹ\s*phẩm|son\s*môi|serum|kem\s*dưỡng)",
        re.IGNORECASE,
    ),
    "comedy": re.compile(
        r"(?:hài|hai\b|skit|parody|prank|troll|meme|giải\s*trí)",
        re.IGNORECASE,
    ),
    "lifestyle": re.compile(
        r"(?:đời\s*sống|doi\s*song|daily\s*vlog|routine|tâm\s*sự|tam\s*su)",
        re.IGNORECASE,
    ),
    "real_estate": _REAL_ESTATE_STRONG_RE,
    "business": re.compile(
        r"(?:kinh\s*doanh|đầu\s*tư|dau\s*tu|crypto|cổ\s*phiếu|startup|tài\s*chính)",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class CrossNicheClassRemapResult:
    remapped: bool
    content_class_id: int | None = None
    previous_slug: str | None = None
    target_slug: str | None = None


def _effective_target_slug(slug: str, haystack: str) -> str:
    """Promote obvious baby/family clips out of lifestyle/comedy/real_estate slugs."""
    if _BABY_FAMILY_RE.search(haystack) and slug in ("lifestyle", "comedy", "real_estate", "business"):
        return "family"
    return slug


def _signals_support_slug(slug: str, haystack: str) -> bool:
    if not haystack.strip():
        return False
    pattern = _NICHE_SIGNAL_RES.get(slug)
    if pattern is None:
        return True
    if not pattern.search(haystack):
        return False
    if slug in ("family", "lifestyle", "comedy", "food", "beauty", "fashion"):
        if _REAL_ESTATE_STRONG_RE.search(haystack) and not _BABY_FAMILY_RE.search(haystack):
            return False
    if slug == "real_estate" and not _REAL_ESTATE_STRONG_RE.search(haystack):
        return False
    return True


def _content_class_for_slug_format(slug: str, format_axis: str | None) -> int | None:
    cn_id = CREATOR_NICHE_SLUG_TO_ID.get(slug)
    if cn_id is None:
        return None
    fmt = str(format_axis or "").strip()
    if fmt:
        cc = content_class_id_for_creator_niche_format(cn_id, fmt)
        if cc is not None:
            return cc
    return content_class_id_for_creator_niche_format(cn_id, "vlog_daily")


def apply_cross_niche_class_remap(
    analysis_json: dict[str, Any],
    *,
    video_id: str = "",
    current_content_class_id: int | None = None,
    loop_creator_niche_id: int | None = None,
) -> CrossNicheClassRemapResult:
    """Re-align ``content_class_id`` when Gemini topic ≠ loop-assigned class primary niche."""
    if not isinstance(analysis_json, dict):
        return CrossNicheClassRemapResult(remapped=False)

    nc_raw = analysis_json.get("niche_classification")
    if not isinstance(nc_raw, dict):
        return CrossNicheClassRemapResult(remapped=False)

    try:
        conf = float(nc_raw.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if conf < _GEMINI_NICHE_CONFIDENCE_FLOOR:
        return CrossNicheClassRemapResult(remapped=False)

    slug_raw = nc_raw.get("creator_niche_slug")
    slug = str(slug_raw).strip() if slug_raw is not None else ""
    if not slug or slug not in CREATOR_NICHE_SLUG_TO_ID:
        return CrossNicheClassRemapResult(remapped=False)

    fmt_axis = str(nc_raw.get("format_axis") or "").strip() or None
    haystack = _analysis_signal_haystack(analysis_json)
    target_slug = _effective_target_slug(slug, haystack)

    if not _signals_support_slug(target_slug, haystack):
        return CrossNicheClassRemapResult(remapped=False, previous_slug=slug)

    target_cn = CREATOR_NICHE_SLUG_TO_ID.get(target_slug)
    if target_cn is None:
        return CrossNicheClassRemapResult(remapped=False, previous_slug=slug)

    loop_cn: int | None = None
    if current_content_class_id is not None:
        loop_cn = primary_creator_niche_id_for_content_class(int(current_content_class_id))
    if loop_cn is None and loop_creator_niche_id is not None:
        loop_cn = int(loop_creator_niche_id)

    if loop_cn is not None and loop_cn == target_cn:
        return CrossNicheClassRemapResult(remapped=False, previous_slug=slug, target_slug=target_slug)

    # Only override HI-11 loop assignments for high-friction loop niches unless
    # primary niche is clearly wrong vs Gemini.
    if loop_cn is not None and loop_cn not in _MISFILE_LOOP_CREATOR_NICHE_IDS:
        gem_cn = CREATOR_NICHE_SLUG_TO_ID.get(slug)
        if gem_cn is None or loop_cn == gem_cn:
            return CrossNicheClassRemapResult(remapped=False, previous_slug=slug)

    if fmt_axis and not junction_has_pair(target_slug, fmt_axis):
        return CrossNicheClassRemapResult(remapped=False, previous_slug=slug, target_slug=target_slug)

    target_cc = _content_class_for_slug_format(target_slug, fmt_axis)
    if target_cc is None:
        return CrossNicheClassRemapResult(remapped=False, previous_slug=slug, target_slug=target_slug)

    if (
        current_content_class_id is not None
        and int(current_content_class_id) == int(target_cc)
        and slug == target_slug
    ):
        return CrossNicheClassRemapResult(
            remapped=False,
            content_class_id=target_cc,
            previous_slug=slug,
            target_slug=target_slug,
        )

    nc = dict(nc_raw)
    previous_slug = slug
    if target_slug != slug:
        nc["creator_niche_slug"] = target_slug
        nc["alternative_creator_niche_slug"] = slug
        rationale = str(nc.get("rationale") or "").strip()
        suffix = (
            f" Nội dung thuộc ngách {target_slug} — chuẩn hoá class junction "
            f"(không giữ class loop {loop_cn or '?'})."
        )
        nc["rationale"] = (rationale + suffix).strip() if rationale else suffix.strip()
    if conf < 0.85:
        nc["confidence"] = 0.85
    analysis_json["niche_classification"] = nc

    logger.info(
        "[cross_niche_remap] video_id=%s slug %s→%s content_class_id %s→%s loop_cn=%s",
        video_id or "?",
        previous_slug,
        target_slug,
        current_content_class_id,
        target_cc,
        loop_cn,
    )
    return CrossNicheClassRemapResult(
        remapped=True,
        content_class_id=target_cc,
        previous_slug=previous_slug,
        target_slug=target_slug,
    )


def resolve_post_route_content_class_id(
    analysis_json: dict[str, Any],
    *,
    route_content_class_id: int | None,
    video_id: str = "",
    loop_creator_niche_id: int | None = None,
) -> int | None:
    """Apply fashion-commerce then cross-niche remaps after HI-11 route."""
    from getviews_pipeline.fashion_commerce_niche_remap import apply_fashion_commerce_niche_remap

    cc = route_content_class_id
    fashion = apply_fashion_commerce_niche_remap(
        analysis_json,
        video_id=video_id,
        current_content_class_id=cc,
    )
    if fashion.remapped and fashion.content_class_id is not None:
        cc = fashion.content_class_id

    cross = apply_cross_niche_class_remap(
        analysis_json,
        video_id=video_id,
        current_content_class_id=cc,
        loop_creator_niche_id=loop_creator_niche_id,
    )
    if cross.remapped and cross.content_class_id is not None:
        cc = cross.content_class_id
    return cc
