from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_MIN_NICHE_SAMPLE_FOR_HOOK_RANK = 30


def _hook_analysis_dict(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return {}
    ha = ua.get("hook_analysis") or {}
    return ha if isinstance(ha, dict) else {}


def extract_hook_first_frame_product_signal(ctx: dict) -> list[Signal]:
    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []

    fft = str(ha.get("first_frame_type") or ha.get("opening_visual") or "").lower()
    hook_type = str(ha.get("hook_type") or "").lower()

    if not fft or "product" in fft or "face" in fft:
        return []
    return [
        Signal(
            id="hook_first_frame_non_product",
            section_id="diagnosis",
            taxonomy_ref="§3",
            salience=0.74,
            claim="Khung mở đầu chưa lộ rõ sản phẩm / kết quả so với pattern review trong nhiều ngách.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"first_frame_type={fft or hook_type}",
                    location="user_analysis.hook_analysis",
                )
            ],
            suggested_fix="Cân nhắc close-up sản phẩm hoặc kết quả trong 0–2s.",
        )
    ]


def extract_hook_type_niche_mismatch_signal(ctx: dict) -> list[Signal]:
    nm = ctx.get("niche_meta") or {}
    if not isinstance(nm, dict):
        return []
    dist = nm.get("hook_distribution")
    if not isinstance(dist, dict) or not dist:
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE_FOR_HOOK_RANK:
        return []

    items = sorted(
        (
            (str(k).strip().lower().replace("-", "_"), int(v))
            for k, v in dist.items()
            if int(v or 0) > 0
        ),
        key=lambda x: -x[1],
    )
    top = [k for k, _ in items[:3]]
    if not top:
        return []

    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []
    ht = str(ha.get("hook_type") or "").strip().lower().replace("-", "_")
    if not ht or ht in ("none", "other"):
        return []

    if ht in top:
        return []
    return [
        Signal(
            id="hook_type_niche_mismatch",
            section_id="diagnosis",
            taxonomy_ref="§3",
            salience=0.75,
            claim=(
                f"Loại hook hiện tại ({ht}) nằm ngoài top hook đang tích lũy view "
                f"trong ngách gần đây ({', '.join(top)}) — cân nhắc lệch / đổi công thức mở."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"hook_type={ht} top_niche_hooks={','.join(top)}",
                    location="user_analysis.hook_analysis+niche_meta.hook_distribution",
                )
            ],
            suggested_fix="Thử align với 1 trong top hook của ngách hoặc chủ đích tách biệt rõ (không lai).",
        )
    ]


def extract_hook_layering_signal(ctx: dict) -> list[Signal]:
    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []
    layering = str(ha.get("hook_layering") or "").lower()
    if layering != "single":
        return []
    return [
        Signal(
            id="hook_layering_single",
            section_id="diagnosis",
            taxonomy_ref="§3",
            salience=0.7,
            claim="Hook đơn lớp — thiếu xếp chồng hình + chữ + âm thanh (chuẩn VN 2025+).",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="hook_layering=single",
                    location="user_analysis.hook_analysis.hook_layering",
                )
            ],
            suggested_fix="Thêm text overlay hoặc lớp âm thanh hỗ trợ hook trong 0–3s.",
        )
    ]


def extract_hook_body_contract_signal(ctx: dict) -> list[Signal]:
    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []
    if ha.get("hook_body_contract") is not False:
        return []
    return [
        Signal(
            id="hook_body_contract_violated",
            section_id="diagnosis",
            taxonomy_ref="§3",
            salience=0.9,
            claim="Thân video không trả lời lời hứa hook — rủi ro rớt retention giữa chừng.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="hook_body_contract=false",
                    location="user_analysis.hook_analysis.hook_body_contract",
                )
            ],
            suggested_fix="Đồng bộ beat đầu với payoff giây 4–12.",
        )
    ]


def extract_dialect_consistency_signal(ctx: dict) -> list[Signal]:
    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []
    ht = str(ha.get("hook_type") or "").lower().replace("-", "_")
    dialect = str(ha.get("dialect_detected") or "none").lower().replace("-", "_")

    if ht == "dialect_identity" and dialect in ("none", "", "neutral"):
        return [
            Signal(
                id="hook_dialect_hook_without_markers",
                section_id="diagnosis",
                taxonomy_ref="§3",
                salience=0.6,
                claim="Hook giọng vùng miền nhưng không gắn dialect_detected — thiếu bằng chứng giọng.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote="hook_type=dialect_identity dialect_detected=none",
                        location="user_analysis.hook_analysis",
                    )
                ],
                suggested_fix="Nếu mở bài dùng giọng địa phương, ghi nhận miền rõ trong hook_line/overlay.",
            )
        ]

    ch = ctx.get("channel_context") or {}
    if isinstance(ch, dict):
        dom = str(ch.get("dominant_dialect") or "").strip().lower().replace("-", "_")
        if dom and dialect not in ("none", "", "neutral") and dom != dialect:
            return [
                Signal(
                    id="hook_dialect_channel_mismatch",
                    section_id="diagnosis",
                    taxonomy_ref="§3",
                    salience=0.6,
                    claim="Giọng/địa phương trong clip lệch với baseline kênh (nếu có dominant_dialect).",
                    evidence=[
                        Evidence(
                            type="user_analysis_field",
                            quote=f"dialect_detected={dialect} dominant_dialect={dom}",
                            location="user_analysis.hook_analysis+channel_context",
                        )
                    ],
                    suggested_fix="Thống nhất persona địa phương hoặc giữ neutral nếu kênh đa miền.",
                )
            ]
    return []


def extract_gia_soc_compliance_signal(ctx: dict) -> list[Signal]:
    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []
    ht = str(ha.get("hook_type") or "").lower().replace("-", "_")
    if ht not in ("gia_soc", "price_shock"):
        return []
    if ha.get("price_anchor_manipulation_suspected") is not True:
        return []
    return [
        Signal(
            id="hook_gia_soc_price_anchor_risk",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=0.85,
            claim=(
                "Hook giá sốc kèm neo giá có dấu hiệu ảo / không khớp Chuẩn TikTok Shop VN — rủi ro comply."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="price_anchor_manipulation_suspected=true",
                    location="user_analysis.hook_analysis.price_anchor_manipulation_suspected",
                )
            ],
            suggested_fix="Neo giá gạch ngang phải là giá niêm yết thật; tránh phóng đại 5×+.",
        )
    ]


def extract_hook_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_hook_first_frame_product_signal(ctx))
    out.extend(extract_hook_type_niche_mismatch_signal(ctx))
    out.extend(extract_hook_layering_signal(ctx))
    out.extend(extract_hook_body_contract_signal(ctx))
    out.extend(extract_dialect_consistency_signal(ctx))
    out.extend(extract_gia_soc_compliance_signal(ctx))
    return out
