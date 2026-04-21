"""Creator-level enrichment helpers for the seller-first KOL finder.

Pure (no I/O) functions that derive `CreatorCard` facts from already-fetched
data: follower count → tier, bio/captions → commerce signals + contact,
in-hand signals → red flags, tier → rate ballpark.

Unit-tested in `tests/test_creator_enrich.py`. Keeping these out of pipelines.py
so the Gemini / Supabase / EnsembleData layers stay thin wrappers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# ── Tier ────────────────────────────────────────────────────────────────────

CreatorTier = Literal["nano", "micro", "macro", "mega"]


def tier_from_followers(followers: int) -> CreatorTier:
    """Canonical follower-band → tier mapping.

    Bands:
      nano  : < 10K   — neighbourhood reach, highest relative engagement
      micro : 10K-100K — the sweet spot for affordable niche campaigns
      macro : 100K-1M — agency-brokered, higher cost, broader reach
      mega  : 1M+     — celebrity tier, enterprise deals
    """
    n = max(0, int(followers or 0))
    if n < 10_000:
        return "nano"
    if n < 100_000:
        return "micro"
    if n < 1_000_000:
        return "macro"
    return "mega"


# ── Rate ballpark (VND per sponsored post) ──────────────────────────────────
# Numbers are first-pass industry estimates. The spec calls these out as
# "ship rough, tune later" — a future `creator_rate_samples` table will upgrade
# confidence from `tier_estimate` to `observed` when price leaks are detected.

_RATE_BANDS: dict[CreatorTier, tuple[int, int]] = {
    "nano": (300_000, 800_000),
    "micro": (1_000_000, 4_000_000),
    "macro": (5_000_000, 15_000_000),
    "mega": (20_000_000, 80_000_000),
}


@dataclass(frozen=True)
class RateBallpark:
    currency: str = "VND"
    low: int = 0
    high: int = 0
    confidence: Literal["observed", "tier_estimate"] = "tier_estimate"

    def asdict(self) -> dict[str, object]:
        return {
            "currency": self.currency,
            "low": self.low,
            "high": self.high,
            "confidence": self.confidence,
        }


def rate_ballpark_for_tier(tier: CreatorTier) -> RateBallpark:
    low, high = _RATE_BANDS[tier]
    return RateBallpark(low=low, high=high, confidence="tier_estimate")


# ── Commerce signals ────────────────────────────────────────────────────────

_TIKTOK_SHOP_RE = re.compile(r"(shop\.tiktok\.com|tiktok\.shop|#tiktokshop)", re.IGNORECASE)
_SHOPEE_RE = re.compile(r"(shopee\.(?:vn|com)|shp\.ee|s\.shopee\.vn)", re.IGNORECASE)
_LAZADA_RE = re.compile(r"lazada\.vn|lzd\.co", re.IGNORECASE)
_AFFILIATE_RE = re.compile(r"(affiliate|tiếp\s*thị\s*liên\s*kết|bit\.ly|l\.me)", re.IGNORECASE)

# Sponsored-post markers in Vietnamese TikTok captions.
_SPONSORED_RE = re.compile(
    r"(#hợp\s*tác|hợp\s*tác\s*có\s*tính\s*phí|#ad\b|#sponsored|#pr\b|\[ad\]|"
    r"quảng\s*cáo|tài\s*trợ|brand\s*deal)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CommerceSignal:
    shop_linked: bool = False
    recent_sponsored_count: int = 0
    competitor_conflicts: tuple[str, ...] = ()

    def asdict(self) -> dict[str, object]:
        return {
            "shop_linked": self.shop_linked,
            "recent_sponsored_count": self.recent_sponsored_count,
            "competitor_conflicts": list(self.competitor_conflicts),
        }


def detect_commerce(
    bio: str,
    captions: list[str],
    *,
    competitor_brands: list[str] | None = None,
) -> CommerceSignal:
    """Scan a creator's bio and recent captions for commerce + brand-conflict signals.

    `competitor_brands` is caller-provided (e.g. "Innisfree", "The Ordinary" — the
    buyer's competitor list). Case-insensitive substring match against caption text.
    """
    haystack = " \n".join([bio or "", *captions])
    shop_linked = bool(
        _TIKTOK_SHOP_RE.search(haystack)
        or _SHOPEE_RE.search(haystack)
        or _LAZADA_RE.search(haystack)
        or _AFFILIATE_RE.search(haystack)
    )
    sponsored_count = sum(1 for cap in captions if _SPONSORED_RE.search(cap))

    conflicts: list[str] = []
    if competitor_brands:
        lower_haystack = haystack.lower()
        for brand in competitor_brands:
            b = brand.strip().lower()
            if b and re.search(rf"\b{re.escape(b)}\b", lower_haystack):
                conflicts.append(brand.strip())

    return CommerceSignal(
        shop_linked=shop_linked,
        recent_sponsored_count=sponsored_count,
        competitor_conflicts=tuple(conflicts),
    )


# ── Contact extraction ─────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
# Vietnamese Zalo/phone markers: "zalo 09xxxxxxx", "0912 345 678", "+84 912 345 678"
_ZALO_RE = re.compile(
    r"(?:zalo[:\s]*|z\s*:\s*|📱|liên\s*hệ[:\s]*)?"
    r"(?:\+?84|0)\s*(?:\d\s*){9}",
    re.IGNORECASE,
)
# Management / agency keywords commonly left in VN creator bios.
_MANAGEMENT_RE = re.compile(
    r"(mcn|agency|management|quản\s*lý|booking)[:\s]*([^\n|]{1,60})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ContactInfo:
    email: str | None = None
    zalo: str | None = None
    management: str | None = None

    def asdict(self) -> dict[str, object]:
        return {
            "email": self.email,
            "zalo": self.zalo,
            "management": self.management,
        }


def _normalize_zalo(raw: str) -> str:
    # Strip zalo / liên hệ prefix, collapse spaces, keep + and digits.
    s = re.sub(r"(?i)(zalo|z|📱|liên\s*hệ)[:\s]*", "", raw).strip()
    digits = re.sub(r"[^\d+]", "", s)
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits


def extract_contact(bio: str) -> ContactInfo:
    if not bio:
        return ContactInfo()
    email = None
    m = _EMAIL_RE.search(bio)
    if m:
        email = m.group(0)

    zalo = None
    z = _ZALO_RE.search(bio)
    if z:
        zalo = _normalize_zalo(z.group(0))
        # Guard against matching isolated 10-digit numbers that aren't phones.
        if len(re.sub(r"[^\d]", "", zalo)) != 10:
            zalo = None

    management = None
    mg = _MANAGEMENT_RE.search(bio)
    if mg:
        management = mg.group(2).strip(" :|-–")
        if len(management) < 2:
            management = None

    return ContactInfo(email=email, zalo=zalo, management=management)


# ── Red flags ──────────────────────────────────────────────────────────────

RedFlag = Literal[
    "engagement_anomaly",
    "post_gap",
    "declining_views",
    "competitor_conflict",
]


def derive_red_flags(
    *,
    days_since_last_post: int | None,
    engagement_trend: str | None,
    median_views_30d: int | None,
    median_views_60d: int | None,
    er_followers_pct: float | None,
    tier: CreatorTier,
    commerce: CommerceSignal,
) -> list[RedFlag]:
    """Derive red-flag chips from signals we already have in the card.

    Rules (all derived — no extra API calls):
    - `post_gap`: days_since_last_post > 14
    - `declining_views`: 30d median < 60% of 60d median (allow for normal dip, catch real drops)
    - `engagement_anomaly`: ER wildly off the expected band for the tier
      (nano: >25% or <0.5%; micro: >15% or <1%; macro: >10% or <0.5%; mega: >8% or <0.3%)
    - `competitor_conflict`: commerce.competitor_conflicts non-empty
    """
    flags: list[RedFlag] = []

    if days_since_last_post is not None and days_since_last_post > 14:
        flags.append("post_gap")

    if (
        median_views_30d is not None
        and median_views_60d is not None
        and median_views_60d > 0
        and median_views_30d < 0.6 * median_views_60d
    ):
        flags.append("declining_views")

    if er_followers_pct is not None:
        bands: dict[CreatorTier, tuple[float, float]] = {
            "nano": (0.5, 25.0),
            "micro": (1.0, 15.0),
            "macro": (0.5, 10.0),
            "mega": (0.3, 8.0),
        }
        lo, hi = bands[tier]
        if er_followers_pct < lo or er_followers_pct > hi:
            flags.append("engagement_anomaly")

    if commerce.competitor_conflicts:
        flags.append("competitor_conflict")

    return flags


# ── Product-context follow-up gating ────────────────────────────────────────

_PRICE_MENTION_RE = re.compile(
    r"(giá|price|\d{2,}k\b|\d{1,3}\.\d{3}|\d+\s*triệu|\d+\s*m\b|vnd|đồng)",
    re.IGNORECASE,
)
_COMPETITOR_MENTION_RE = re.compile(
    r"(đối\s*thủ|competitor|so\s*với|vs\.?)", re.IGNORECASE
)


def needs_product_context(query: str, persona_empty: bool) -> bool:
    """Return True when the query lacks the product-context slots that would
    sharpen a creator shortlist. Trigger the conversational follow-up chip
    only when we'd genuinely learn something new from the next turn.

    If persona_empty is False (the user already mentioned pain_points / age /
    geography) we still want to know about price + competitors — sellers who
    know their persona often don't know their rival list.
    """
    q = query or ""
    has_price = bool(_PRICE_MENTION_RE.search(q))
    has_competitor = bool(_COMPETITOR_MENTION_RE.search(q))
    if has_price and has_competitor and not persona_empty:
        return False
    # Ask when any of the three is missing.
    return True


@dataclass(frozen=True)
class ActionChip:
    type: Literal["brief", "deep_dive", "sponsored_history", "similar"]
    prompt: str


def default_actions(handle: str, niche_label: str) -> list[ActionChip]:
    """Action chips rendered under each creator card.

    Prompts are Vietnamese, re-route through the existing intent router:
    - "brief" → brief_generation (paid)
    - "deep_dive" → competitor_profile when an @handle is present (paid)
    - "similar" → creator_search with modifier (free)
    - "sponsored_history" → follow_up (free — just a chat turn)
    """
    h = handle.lstrip("@")
    return [
        ActionChip(type="brief", prompt=f"Tạo brief cho @{h}"),
        ActionChip(type="deep_dive", prompt=f"Phân tích chi tiết @{h}"),
        ActionChip(type="sponsored_history", prompt=f"Xem các post sponsored gần đây của @{h}"),
        ActionChip(type="similar", prompt=f"Tìm thêm creator tương tự @{h}"),
    ]


__all__ = [
    "ActionChip",
    "CommerceSignal",
    "ContactInfo",
    "CreatorTier",
    "RateBallpark",
    "RedFlag",
    "default_actions",
    "derive_red_flags",
    "detect_commerce",
    "extract_contact",
    "needs_product_context",
    "rate_ballpark_for_tier",
    "tier_from_followers",
]
