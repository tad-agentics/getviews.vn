from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal


def _as_commerce_dict(ua: dict) -> dict[str, Any]:
    raw = ua.get("commerce_intent")
    return raw if isinstance(raw, dict) else {}


def _is_commercial(ua: dict, ci: dict[str, Any]) -> bool:
    promo = str(ua.get("promotion_type") or "organic").lower()
    if promo not in ("organic", ""):
        return True
    obj = str(ci.get("conversion_objective") or "entertainment_first").lower()
    return obj != "entertainment_first"


def extract_restricted_phrase_compliance_signals(ctx: dict) -> list[Signal]:
    flags = ctx.get("compliance_flags") or []
    phrase_flags = [
        f
        for f in flags
        if isinstance(f, dict)
        and str(f.get("category"))
        in ("health_claim", "price_guarantee", "off_platform", "violence")
    ]
    if not phrase_flags:
        return []
    high = [f for f in phrase_flags if str(f.get("severity")) == "high"]
    picked = high if high else phrase_flags
    salience = 1.0 if high else 0.82
    first = picked[0]
    phrase = str(first.get("phrase") or "")
    claim = (
        f"Phát hiện cụm từ vi phạm chính sách TikTok ({len(picked)} hit): "
        f"{phrase[:100]}"
    )
    evidence = [
        Evidence(
            type="user_analysis_field",
            quote=str(f.get("phrase") or "")[:200],
            location=str(f.get("location") or "—"),
        )
        for f in picked[:4]
    ]
    return [
        Signal(
            id="compliance_restricted_phrase",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=salience,
            claim=claim,
            evidence=evidence,
            suggested_fix=(
                "Gỡ cụm từ cấm theo Community Guidelines TikTok; thay bằng claim có "
                "kiểm chứng và tránh đẩy người xem ra nền tảng khác."
            ),
        )
    ]


def extract_price_anchor_compliance_signal(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ha = ua.get("hook_analysis") if isinstance(ua.get("hook_analysis"), dict) else {}
    flags = ctx.get("compliance_flags") or []
    from_scan = any(
        isinstance(f, dict) and str(f.get("category")) == "price_anchor_inflated"
        for f in flags
    )
    if from_scan:
        phrase = next(
            (
                str(f.get("phrase"))
                for f in flags
                if isinstance(f, dict) and str(f.get("category")) == "price_anchor_inflated"
            ),
            "neo giá ≥5×",
        )
        return [
            Signal(
                id="compliance_price_anchor_inflated",
                section_id="compliance",
                taxonomy_ref="§10",
                salience=0.85,
                claim=(
                    "Dấu hiệu neo giá phóng đại (≥5×) trên VO/chữ — rủi ro "
                    "Neo giá TikTok Shop VN."
                ),
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote=phrase[:240],
                        location="compliance_flags.price_anchor_inflated",
                    )
                ],
                suggested_fix="Chỉ gạch giá mức đã niêm yết thật; tránh chênh 5×+ so với giá bán.",
            )
        ]
    if ha.get("price_anchor_manipulation_suspected") is True:
        ht = str(ha.get("hook_type") or "").lower().replace("-", "_")
        if ht not in ("gia_soc", "price_shock"):
            return [
                Signal(
                    id="compliance_price_anchor_inflated",
                    section_id="compliance",
                    taxonomy_ref="§10",
                    salience=0.85,
                    claim=(
                        "Gemini đánh dấu neo giá có dấu hiệu thao túng — kiểm tra "
                        "khớp giá niêm yết thật."
                    ),
                    evidence=[
                        Evidence(
                            type="user_analysis_field",
                            quote="price_anchor_manipulation_suspected=true",
                            location="user_analysis.hook_analysis",
                        )
                    ],
                    suggested_fix="Đối chiếu giá gốc với lịch sử Shop; không phóng đại neo giá.",
                )
            ]
    return []


def extract_disclosure_compliance_signal(ctx: dict) -> list[Signal]:
    """Ad Law 2025 — compliance section (dịch vụ §10; commerce section giữ §0)."""
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    ci = _as_commerce_dict(ua)
    promo = str(ua.get("promotion_type") or "organic").lower()
    if not _is_commercial(ua, ci):
        return []
    if ci:
        if ci.get("disclosure_present"):
            return []
        quote = "disclosure_present=false"
        loc = "user_analysis.commerce_intent.disclosure_present"
    else:
        if promo not in ("brand_deal", "affiliate"):
            return []
        quote = f"promotion_type={promo} (không có commerce_intent.disclosure)"
        loc = "user_analysis.promotion_type"
    return [
        Signal(
            id="compliance_ad_law_disclosure_missing",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=0.9,
            claim=(
                "Quan hệ thương mại hiển nhiên nhưng thiếu tiết lộ rõ — rủi ro "
                "Luật Quảng cáo VN 2025."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=quote,
                    location=loc,
                )
            ],
            suggested_fix="Thêm tiết lộ voice/#qc/chữ nổi theo Khung an toàn quảng cáo.",
        )
    ]


def extract_safe_zone_compliance_signal(ctx: dict) -> list[Signal]:
    flags = ctx.get("compliance_flags") or []
    hits = [f for f in flags if isinstance(f, dict) and str(f.get("category")) == "safe_zone"]
    if not hits:
        return []
    return [
        Signal(
            id="compliance_safe_zone_bottom",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=0.88,
            claim=(
                "Chữ hoặc CTA giá/mua nằm vùng dưới khung — vi phạm vùng an toàn TikTok "
                "(dễ bị che bởi nút Shop/giỏ)."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=str(hits[0].get("phrase") or "bottom_overlay_risk"),
                    location="user_analysis.safe_zone_status",
                )
            ],
            suggested_fix="Đẩy giá, CTA và mã giảm giá lên giữa/trên 50% khung hình.",
        )
    ]


def extract_engagement_bait_hashtag_signal(ctx: dict) -> list[Signal]:
    flags = ctx.get("compliance_flags") or []
    bait = [
        f
        for f in flags
        if isinstance(f, dict) and str(f.get("category")) in ("engagement_bait", "hashtag_noise")
    ]
    if not bait:
        return []
    phrase = str(bait[0].get("phrase") or "")
    return [
        Signal(
            id="compliance_engagement_bait_hashtag",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=0.72,
            claim=(
                f"Caption có hashtag/pattern dễ bị coi là câu view ({len(bait)} hit) — "
                "rủi ro spam theo chính sách tương tác TikTok."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=str(f.get("phrase") or "")[:120],
                    location=str(f.get("location") or "caption"),
                )
                for f in bait[:3]
            ],
            suggested_fix="Bỏ hashtag f4f/sub4sub; dùng hashtag ngách tiếng Việt + caption mô tả nội dung.",
        )
    ]


def extract_copyright_music_compliance_signal(ctx: dict) -> list[Signal]:
    """Business / ads path — nhạc không CML-safe."""
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    st = ctx.get("user_stats") if isinstance(ctx.get("user_stats"), dict) else {}
    prof = st.get("trending_sound_profile")
    acct = str(ua.get("tiktok_account_type_heuristic") or "").strip().lower()
    music = str(st.get("music_title") or "").strip()

    if isinstance(prof, dict) and prof.get("commercial_music_library_eligible") is False:
        return [
            Signal(
                id="compliance_cml_music_risk",
                section_id="compliance",
                taxonomy_ref="§10",
                salience=0.84,
                claim=(
                    "Nhạc nền không thuộc Commercial Music Library — video có thể bị "
                    "mute/strip hoặc hạn chế phân phối khi chạy quảng cáo."
                ),
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote=f"commercial_music_library_eligible=false title={music[:80]}",
                        location="user_stats.trending_sound_profile",
                    )
                ],
                suggested_fix="Đổi sang nhạc CML hoặc original có quyền sử dụng rõ trong TikTok.",
            )
        ]

    if acct == "business" and ua.get("trending_vpop_sound") is True:
        return [
            Signal(
                id="compliance_business_trending_sound",
                section_id="compliance",
                taxonomy_ref="§10",
                salience=0.78,
                claim=(
                    "Tài khoản business dùng nhạc trending V-pop — rủi ro bản quyền / "
                    "giới hạn CML khi boost hoặc Spark Ads."
                ),
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote=f"tiktok_account_type_heuristic=business music={music[:80]}",
                        location="user_analysis+user_stats",
                    )
                ],
                suggested_fix="Ưu tiên nhạc từ thư viện CML trong TikTok trước khi chạy ads.",
            )
        ]
    return []


def extract_ai_disclosure_compliance_signal(ctx: dict) -> list[Signal]:
    """§10 — AI-generated/modified content without platform or in-video disclosure."""
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return []
    flags = ctx.get("compliance_flags") or []
    hits = [f for f in flags if isinstance(f, dict) and str(f.get("category")) == "ai_disclosure"]
    if not hits and ua.get("ai_generated_suspected") is not True:
        return []
    if not hits and ua.get("ai_disclosure_present") is True:
        return []
    if not hits:
        return []
    ci = _as_commerce_dict(ua)
    commercial = _is_commercial(ua, ci)
    salience = 0.92 if commercial else 0.86
    form = str(ua.get("ai_disclosure_form") or "none")
    claim = (
        "Clip có dấu hiệu AI/synthetic (deepfake, avatar, nền generative, TTS…) "
        "nhưng chưa thấy nhãn TikTok AIGC hoặc tiết lộ rõ trong caption/overlay/voice — "
        "rủi ro từ chối quảng cáo và hạn chế phân phối."
    )
    if commercial:
        claim = (
            claim + " Clip thương mại — ưu tiên bật nhãn AIGC trước khi boost/Spark Ads."
        )
    return [
        Signal(
            id="compliance_ai_disclosure_missing",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=salience,
            claim=claim,
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=(
                        f"ai_generated_suspected=true ai_disclosure_present=false "
                        f"ai_disclosure_form={form}"
                    ),
                    location="user_analysis.ai_disclosure_*",
                )
            ],
            suggested_fix=(
                "Bật nhãn AIGC/synthetic trên TikTok hoặc thêm chữ overlay/caption "
                "#AI / “tạo bằng AI” trước khi đăng hoặc chạy ads."
            ),
        )
    ]


def extract_shadowban_distribution_risk_signal(ctx: dict) -> list[Signal]:
    """Heuristic: views << kênh median nhưng ER mặt nổi cao — dấu hiệu tương tác chéo / throttle."""
    st = ctx.get("user_stats") if isinstance(ctx.get("user_stats"), dict) else {}
    ch = ctx.get("channel_context") if isinstance(ctx.get("channel_context"), dict) else {}
    if not ch.get("available"):
        return []
    median_raw = ch.get("median_views")
    if median_raw is None:
        return []
    try:
        median_v = float(median_raw)
    except (TypeError, ValueError):
        return []
    views = int(st.get("views") or 0)
    if median_v <= 0 or views <= 0:
        return []
    ratio = views / median_v
    if ratio > 0.5:
        return []
    er = float(st.get("engagement_rate") or 0.0)
    if er < 0.055:
        return []
    ret = st.get("retention_end_pct")
    if ret is not None:
        try:
            ret_f = float(ret)
        except (TypeError, ValueError):
            ret_f = None
        else:
            # Retention curve stores 0–100 (%); treat ≥62% as "decent hook-body hold".
            if ret_f >= 62.0:
                return []
    return [
        Signal(
            id="compliance_shadowban_cheo_signature",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=0.7,
            claim=(
                f"Lượt xem chỉ ~{ratio:.0%} median kênh ({views:,} vs median ~{int(median_v):,}) "
                f"nhưng ER mặt nổi {er:.1%} — nghi tương tác chéo hoặc throttle phân phối."
            ),
            evidence=[
                Evidence(
                    type="channel_field",
                    quote=f"views={views} median_views={int(median_v)} engagement_rate={er}",
                    location="user_stats+channel_context",
                )
            ],
            suggested_fix=(
                "Giảm seed nhóm chéo; ưu tiên watch-time và chia sẻ tự nhiên; "
                "soi Nguồn lưu lượng trong TikTok Studio."
            ),
        )
    ]


def extract_legacy_compliance_hit(ctx: dict) -> list[Signal]:
    """Single generic hit when flags exist but no structured extractor fired."""
    flags = ctx.get("compliance_flags") or []
    if not flags:
        return []
    if extract_restricted_phrase_compliance_signals(ctx):
        return []
    if extract_price_anchor_compliance_signal(ctx):
        return []
    handled_cats = frozenset(
        {
            "health_claim",
            "price_guarantee",
            "off_platform",
            "violence",
            "price_anchor_inflated",
            "safe_zone",
            "engagement_bait",
            "hashtag_noise",
            "ai_disclosure",
        }
    )
    if any(
        isinstance(f, dict) and str(f.get("category")) in handled_cats for f in flags
    ):
        return []
    first = flags[0] if isinstance(flags[0], dict) else {}
    phrase = str(first.get("phrase") or first.get("text") or "restricted content")
    return [
        Signal(
            id="compliance_hit",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=1.0,
            claim=f"Phát hiện dấu hiệu vi phạm chính sách: {phrase[:80]}",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=phrase[:200],
                    location=str(first.get("location") or "compliance_flags[0]"),
                )
            ],
            suggested_fix=(
                "Viết lại theo Khung an toàn quảng cáo và chú thích #qc / voice "
                "khi có quan hệ thương mại."
            ),
        )
    ]


def extract_compliance_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_restricted_phrase_compliance_signals(ctx))
    out.extend(extract_price_anchor_compliance_signal(ctx))
    out.extend(extract_safe_zone_compliance_signal(ctx))
    out.extend(extract_engagement_bait_hashtag_signal(ctx))
    out.extend(extract_copyright_music_compliance_signal(ctx))
    out.extend(extract_disclosure_compliance_signal(ctx))
    out.extend(extract_ai_disclosure_compliance_signal(ctx))
    out.extend(extract_shadowban_distribution_risk_signal(ctx))
    out.extend(extract_legacy_compliance_hit(ctx))
    return out
