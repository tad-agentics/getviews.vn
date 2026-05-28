"""Deterministic fashion-commerce niche remap (Shopee/Lazada affiliate guard).

When Gemini (or legacy ingest) labels fashion/accessories commerce as ``business``,
re-map ``niche_classification.creator_niche_slug`` → ``fashion`` and align
``content_class_id`` to the fashion junction for the detected ``format_axis``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from getviews_pipeline.junction_content_class import content_class_id_for_creator_niche_format
from getviews_pipeline.profile_niches import CREATOR_NICHE_SLUG_TO_ID

logger = logging.getLogger(__name__)

_FASHION_CREATOR_NICHE_ID = CREATOR_NICHE_SLUG_TO_ID["fashion"]

# Business-only content classes that mis-file fashion Shopee reviews.
_BUSINESS_COMMERCE_CLASS_IDS: frozenset[int] = frozenset({47, 48, 49})

_FASHION_PRODUCT_RE = re.compile(
    r"(?:"
    r"quần\s*áo|thời\s*trang|outfit|ootd|phụ\s*kiện|phu\s*kien|"
    r"giày|giay|dép|dep|sneaker|sandals?|"
    r"túi\s*xách|tui\s*xach|handbag|clutch|backpack|"
    r"trang\s*sức|trang\s*suc|jewelry|necklace|earring|"
    r"váy|vay|dress|blazer|cardigan|hoodie|jeans|legging|"
    r"lookbook|phối\s*đồ|phoi\s*do|set\s*đồ|"
    r"accessories|apparel|clothing|belt|mũ\b|kính\s*mát|"
    r" áo |ao\s*thun|ao\s*khoac|jacket|coat\b"
    r")",
    re.IGNORECASE,
)

_COMMERCE_AFFILIATE_RE = re.compile(
    r"(?:"
    r"shopee|lazada|tiktok\s*shop|affiliate|link\s*bio|"
    r"mua\s*ngay|săn\s*sale|san\s*sale|voucher|giỏ\s*hàng|gio\s*hang|"
    r"flash\s*sale|live\s*stream\s*bán|bán\s*hàng\s*online"
    r")",
    re.IGNORECASE,
)

_PURE_BUSINESS_TOPIC_RE = re.compile(
    r"(?:"
    r"đầu\s*tư|dau\s*tu|crypto|bitcoin|cổ\s*phiếu|co\s*phieu|"
    r"bất\s*động\s*sản|bat\s*dong\s*san|startup|quản\s*trị\s*doanh\s*nghiệp|"
    r"kế\s*toán|ke\s*toan|tài\s*chính\s*cá\s*nhân(?!.*thời\s*trang)"
    r")",
    re.IGNORECASE,
)

_BEAUTY_ONLY_RE = re.compile(
    r"(?:"
    r"skincare|serum|kem\s*dưỡng|makeup|mỹ\s*phẩm|my\s*pham|"
    r"son\s*môi|nước\s*hoa|tẩy\s*trang|retinol|vitamin\s*c"
    r")",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FashionCommerceRemapResult:
    remapped: bool
    content_class_id: int | None = None
    previous_slug: str | None = None


def _analysis_signal_haystack(analysis_json: dict[str, Any]) -> str:
    parts: list[str] = []
    cc = analysis_json.get("content_context")
    if isinstance(cc, dict):
        parts.append(str(cc.get("subject_matter") or ""))
        for subj in cc.get("primary_subjects") or []:
            parts.append(str(subj))
        for product in cc.get("products_mentioned") or []:
            if isinstance(product, dict):
                parts.extend(
                    [
                        str(product.get("name") or ""),
                        str(product.get("brand") or ""),
                        str(product.get("category") or ""),
                    ]
                )
        parts.append(str(cc.get("content_purpose") or ""))
        for tag in cc.get("topical_hashtags_implied") or []:
            parts.append(str(tag))
        for action in cc.get("dominant_actions") or []:
            parts.append(str(action))
    parts.append(str(analysis_json.get("audio_transcript") or ""))
    ci = analysis_json.get("commerce_intent")
    if isinstance(ci, dict):
        parts.append(str(ci.get("verbal_cta_quote") or ""))
        parts.append(str(ci.get("conversion_objective") or ""))
    nc = analysis_json.get("niche_classification")
    if isinstance(nc, dict):
        parts.append(str(nc.get("rationale") or ""))
    return " ".join(p for p in parts if p).lower()


def has_fashion_commerce_signals(analysis_json: dict[str, Any]) -> bool:
    """True when analysis text signals fashion/accessories (optionally Shopee affiliate)."""
    if not isinstance(analysis_json, dict):
        return False
    haystack = _analysis_signal_haystack(analysis_json)
    if not haystack:
        return False
    if _PURE_BUSINESS_TOPIC_RE.search(haystack):
        return False
    if not _FASHION_PRODUCT_RE.search(haystack):
        return False
    if _BEAUTY_ONLY_RE.search(haystack) and not _FASHION_PRODUCT_RE.search(haystack):
        return False
    cc = analysis_json.get("content_context")
    purpose = ""
    if isinstance(cc, dict):
        purpose = str(cc.get("content_purpose") or "").lower()
    if purpose in ("sell", "review"):
        return True
    if _COMMERCE_AFFILIATE_RE.search(haystack):
        return True
    nc = analysis_json.get("niche_classification")
    fmt = ""
    if isinstance(nc, dict):
        fmt = str(nc.get("format_axis") or "").lower()
    if fmt in ("review_unboxing", "montage_highlights", "pov_storytelling", "vlog_daily"):
        return True
    return bool(_FASHION_PRODUCT_RE.search(haystack))


def _fashion_content_class_for_format(format_axis: str | None) -> int | None:
    fmt = str(format_axis or "").strip()
    if fmt:
        cc = content_class_id_for_creator_niche_format(_FASHION_CREATOR_NICHE_ID, fmt)
        if cc is not None:
            return cc
    return content_class_id_for_creator_niche_format(
        _FASHION_CREATOR_NICHE_ID, "review_unboxing"
    )


def apply_fashion_commerce_niche_remap(
    analysis_json: dict[str, Any],
    *,
    video_id: str = "",
    current_content_class_id: int | None = None,
) -> FashionCommerceRemapResult:
    """Mutate ``analysis_json`` in place when business mislabels fashion commerce."""
    if not isinstance(analysis_json, dict):
        return FashionCommerceRemapResult(remapped=False)
    if not has_fashion_commerce_signals(analysis_json):
        return FashionCommerceRemapResult(remapped=False)

    nc_raw = analysis_json.get("niche_classification")
    nc: dict[str, Any] = dict(nc_raw) if isinstance(nc_raw, dict) else {}
    previous_slug = str(nc.get("creator_niche_slug") or "").strip() or None
    slug = previous_slug or ""

    if slug and slug not in ("business", "fashion"):
        return FashionCommerceRemapResult(remapped=False, previous_slug=previous_slug)

    fmt_axis = str(nc.get("format_axis") or "").strip() or None
    target_cc = _fashion_content_class_for_format(fmt_axis)

    slug_needs_remap = slug in ("", "business")
    class_needs_realign = (
        current_content_class_id is not None
        and int(current_content_class_id) in _BUSINESS_COMMERCE_CLASS_IDS
        and target_cc is not None
        and int(current_content_class_id) != int(target_cc)
    )

    if not slug_needs_remap and not class_needs_realign:
        return FashionCommerceRemapResult(
            remapped=False,
            content_class_id=target_cc,
            previous_slug=previous_slug,
        )

    if slug_needs_remap:
        nc["creator_niche_slug"] = "fashion"
        if previous_slug == "business":
            nc["alternative_creator_niche_slug"] = "business"
        rationale = str(nc.get("rationale") or "").strip()
        suffix = (
            " Nội dung bán/review thời trang trên sàn — chuẩn hoá ngách fashion "
            "(không phải kinh doanh chung)."
        )
        nc["rationale"] = (rationale + suffix).strip() if rationale else suffix.strip()
        try:
            conf = float(nc.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        if conf < 0.85:
            nc["confidence"] = 0.85

    analysis_json["niche_classification"] = nc

    logger.info(
        "[fashion_commerce_remap] video_id=%s slug %s→fashion content_class_id→%s",
        video_id or "?",
        previous_slug or "?",
        target_cc,
    )
    return FashionCommerceRemapResult(
        remapped=True,
        content_class_id=target_cc,
        previous_slug=previous_slug,
    )
