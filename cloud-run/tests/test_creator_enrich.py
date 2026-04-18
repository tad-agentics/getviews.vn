"""Unit tests for the creator-enrichment helpers (Phase 1 KOL finder)."""

from __future__ import annotations

from getviews_pipeline.creator_enrich import (
    CommerceSignal,
    ContactInfo,
    RateBallpark,
    default_actions,
    derive_red_flags,
    detect_commerce,
    extract_contact,
    needs_product_context,
    rate_ballpark_for_tier,
    tier_from_followers,
)


# ── Tier ────────────────────────────────────────────────────────────────────


def test_tier_nano_below_10k() -> None:
    assert tier_from_followers(0) == "nano"
    assert tier_from_followers(9_999) == "nano"


def test_tier_micro_10k_to_100k() -> None:
    assert tier_from_followers(10_000) == "micro"
    assert tier_from_followers(47_000) == "micro"
    assert tier_from_followers(99_999) == "micro"


def test_tier_macro_100k_to_1m() -> None:
    assert tier_from_followers(100_000) == "macro"
    assert tier_from_followers(750_000) == "macro"


def test_tier_mega_over_1m() -> None:
    assert tier_from_followers(1_000_000) == "mega"
    assert tier_from_followers(12_500_000) == "mega"


def test_tier_rejects_bad_input() -> None:
    # Negative / None shouldn't crash — fallback to nano.
    assert tier_from_followers(-100) == "nano"
    assert tier_from_followers(0) == "nano"


# ── Rate ballpark ──────────────────────────────────────────────────────────


def test_rate_ballpark_shapes() -> None:
    for tier, expected_low_max in [("nano", 800_000), ("micro", 4_000_000),
                                    ("macro", 15_000_000), ("mega", 80_000_000)]:
        b = rate_ballpark_for_tier(tier)  # type: ignore[arg-type]
        assert isinstance(b, RateBallpark)
        assert b.currency == "VND"
        assert b.low > 0
        assert b.high == expected_low_max
        assert b.confidence == "tier_estimate"


# ── Commerce detection ─────────────────────────────────────────────────────


def test_detect_commerce_shop_linked_from_bio() -> None:
    sig = detect_commerce("Liên hệ: shopee.vn/mystore", captions=[])
    assert sig.shop_linked


def test_detect_commerce_shop_linked_from_caption() -> None:
    sig = detect_commerce("", captions=["Full link TikTok Shop của mình: shop.tiktok.com/...", ""])
    assert sig.shop_linked


def test_detect_commerce_counts_sponsored_posts() -> None:
    sig = detect_commerce(
        "",
        captions=[
            "Review serum mới #hợp tác với brand X",
            "Day in my life",
            "#ad chào tuần mới",
            "",
            "Hợp tác có tính phí — thanks Brand Y",
        ],
    )
    assert sig.recent_sponsored_count == 3


def test_detect_commerce_no_false_positive() -> None:
    sig = detect_commerce("just skincare lover", captions=["weekend vibes", "new serum review"])
    assert not sig.shop_linked
    assert sig.recent_sponsored_count == 0


def test_detect_commerce_competitor_conflict() -> None:
    sig = detect_commerce(
        "",
        captions=[
            "Dùng Innisfree Green Tea serum 3 tháng qua kết quả: da căng hơn",
            "Không liên quan",
        ],
        competitor_brands=["Innisfree", "The Ordinary"],
    )
    assert "Innisfree" in sig.competitor_conflicts
    assert "The Ordinary" not in sig.competitor_conflicts


# ── Contact extraction ─────────────────────────────────────────────────────


def test_extract_contact_email() -> None:
    c = extract_contact("liên hệ: thao.tran@gmail.com · zalo 0912345678")
    assert c.email == "thao.tran@gmail.com"


def test_extract_contact_zalo_variants() -> None:
    assert extract_contact("zalo: 0912 345 678").zalo == "0912345678"
    assert extract_contact("Liên hệ +84 987 654 321").zalo == "0987654321"
    assert extract_contact("hotline 0911 222 333").zalo == "0911222333"


def test_extract_contact_management() -> None:
    c = extract_contact("Management: ABC MCN | booking@abc.vn")
    assert c.management == "ABC MCN"
    assert c.email == "booking@abc.vn"


def test_extract_contact_none() -> None:
    c = extract_contact("just a skincare girl in HCMC")
    assert c.email is None
    assert c.zalo is None
    assert c.management is None


# ── Red flag derivation ────────────────────────────────────────────────────


def test_red_flag_post_gap() -> None:
    flags = derive_red_flags(
        days_since_last_post=20,
        engagement_trend="stable",
        median_views_30d=10_000,
        median_views_60d=10_000,
        er_followers_pct=5.0,
        tier="micro",
        commerce=CommerceSignal(),
    )
    assert "post_gap" in flags


def test_red_flag_declining_views() -> None:
    flags = derive_red_flags(
        days_since_last_post=3,
        engagement_trend="declining",
        median_views_30d=4_000,
        median_views_60d=10_000,
        er_followers_pct=5.0,
        tier="micro",
        commerce=CommerceSignal(),
    )
    assert "declining_views" in flags


def test_red_flag_engagement_anomaly_bot_suspicion() -> None:
    # Micro creator with impossible ER suggests inflated engagement.
    flags = derive_red_flags(
        days_since_last_post=2,
        engagement_trend="stable",
        median_views_30d=10_000,
        median_views_60d=10_000,
        er_followers_pct=40.0,
        tier="micro",
        commerce=CommerceSignal(),
    )
    assert "engagement_anomaly" in flags


def test_red_flag_competitor_conflict() -> None:
    flags = derive_red_flags(
        days_since_last_post=1,
        engagement_trend="rising",
        median_views_30d=20_000,
        median_views_60d=18_000,
        er_followers_pct=6.0,
        tier="micro",
        commerce=CommerceSignal(competitor_conflicts=("Innisfree",)),
    )
    assert "competitor_conflict" in flags


def test_red_flag_clean_creator_has_none() -> None:
    flags = derive_red_flags(
        days_since_last_post=2,
        engagement_trend="rising",
        median_views_30d=20_000,
        median_views_60d=18_000,
        er_followers_pct=6.0,
        tier="micro",
        commerce=CommerceSignal(),
    )
    assert flags == []


# ── Product-context follow-up gating ───────────────────────────────────────


def test_needs_context_when_persona_empty() -> None:
    # Generic query, nothing personalised.
    assert needs_product_context("Tìm creator skincare cho tôi", persona_empty=True)


def test_needs_context_when_price_missing() -> None:
    # Has persona but no price / competitor info.
    assert needs_product_context(
        "Tìm creator skincare cho da dầu 18-25 tuổi", persona_empty=False,
    )


def test_does_not_need_context_when_all_slots_present() -> None:
    q = "Tìm creator skincare cho da dầu 18-25 tuổi, giá 300k, đối thủ Innisfree"
    assert not needs_product_context(q, persona_empty=False)


# ── Default actions ────────────────────────────────────────────────────────


def test_default_actions_shape() -> None:
    chips = default_actions("@thaotranbeauty", "skincare")
    assert len(chips) == 4
    assert all(c.prompt.startswith("T") or c.prompt.startswith("X") or c.prompt.startswith("P") for c in chips)
    assert {c.type for c in chips} == {"brief", "deep_dive", "sponsored_history", "similar"}
