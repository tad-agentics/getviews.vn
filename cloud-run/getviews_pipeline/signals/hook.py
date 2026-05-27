from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_HOOK_SPECIFICITY_MARKERS = re.compile(
    r"[\d?]|tại\s+sao|vì\s+sao|mẹo|cách\s+|review|so\s+sánh|"
    r"\d+\s*(k|tr|triệu|%)|shop|shopee|lỗi|sai|tại\s+ao",
    re.IGNORECASE,
)

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
            section_id="hook_analysis",
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
            section_id="hook_analysis",
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
            section_id="hook_analysis",
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
            section_id="hook_analysis",
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


def _user_transitions_per_second(ctx: dict) -> float | None:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return None
    raw = ua.get("transitions_per_second")
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val >= 0 else None


def _hook_timeline_events_in_window(ha: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = ha.get("hook_timeline")
    if not isinstance(timeline, list):
        return []
    out: list[dict[str, Any]] = []
    for ev in timeline:
        if not isinstance(ev, dict):
            continue
        raw_t = ev.get("t")
        if raw_t is None:
            continue
        try:
            t = float(raw_t)
        except (TypeError, ValueError):
            continue
        if 0.0 <= t <= 3.0:
            out.append(ev)
    return out


def extract_hook_timeline_pacing_signal(ctx: dict) -> list[Signal]:
    """P1 — sparse hook_timeline (<2 events in 0–3s) vs Gemini 2–5 event norm."""
    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []
    events = _hook_timeline_events_in_window(ha)
    if len(events) >= 2:
        return []
    return [
        Signal(
            id="hook_timeline_pacing_sparse",
            section_id="hook_analysis",
            taxonomy_ref="§3",
            salience=0.68,
            claim=(
                f"Cửa sổ hook chỉ có {len(events)} sự kiện timeline (0–3s) — "
                "nhịp mở thưa hơn chuẩn 2–5 beat trong ngách VN."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"hook_timeline_events_0_3s={len(events)}",
                    location="user_analysis.hook_analysis.hook_timeline",
                )
            ],
            suggested_fix=(
                "Thêm ít nhất 1 beat (cut, text overlay, hoặc reveal) trước giây 3 "
                "để giữ nhịp dừng lướt."
            ),
        )
    ]


def extract_hook_pacing_cut_frequency_signal(ctx: dict) -> list[Signal]:
    """P1 — whole-video cut pace vs niche avg (hook section)."""
    nm = ctx.get("niche_meta") or {}
    if not isinstance(nm, dict):
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE_FOR_HOOK_RANK:
        return []

    tps = _user_transitions_per_second(ctx)
    avg_raw = nm.get("avg_transitions_per_second")
    if tps is None or avg_raw is None:
        return []
    try:
        avg = float(avg_raw)
    except (TypeError, ValueError):
        return []
    if avg <= 0:
        return []

    ratio = tps / avg
    if ratio >= 0.75:
        return []

    return [
        Signal(
            id="hook_pacing_cut_frequency",
            section_id="hook_analysis",
            taxonomy_ref="§3",
            salience=0.71,
            claim=(
                f"Tốc độ cắt {tps:.2f}/s thấp hơn ~{int(round((1 - ratio) * 100))}% "
                f"so TB ngách ({avg:.2f}/s) — hook dễ chậm so pattern đang chạy."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"transitions_per_second={tps:.3f} niche_avg={avg:.3f}",
                    location="user_analysis.transitions_per_second+niche_meta.avg_transitions_per_second",
                )
            ],
            suggested_fix=(
                "Thêm 1–2 cú cắt cảnh nhanh (jump-cut) hoặc zoom cận trong 3 giây đầu để nhịp độ khớp với ngách."
            ),
        )
    ]


def extract_hook_vague_specificity_signal(ctx: dict) -> list[Signal]:
    """P1 — hook_phrase thiếu số liệu / câu hỏi / pain cụ thể."""
    ha = _hook_analysis_dict(ctx)
    if not ha:
        return []
    phrase = str(ha.get("hook_phrase") or "").strip()
    if len(phrase) < 4:
        return []
    if _HOOK_SPECIFICITY_MARKERS.search(phrase):
        return []
    if len(phrase) >= 30:
        return []
    return [
        Signal(
            id="hook_vague_specificity",
            section_id="hook_analysis",
            taxonomy_ref="§4.8.3",
            salience=0.73,
            claim=(
                f"Hook mở `{phrase[:48]}` thiếu chi tiết cụ thể (số, câu hỏi, pain) — "
                "dễ bị lướt qua trước khi payoff."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"hook_phrase={phrase[:120]}",
                    location="user_analysis.hook_analysis.hook_phrase",
                )
            ],
            suggested_fix=(
                "Thêm 1 con số, câu hỏi mở, hoặc pain cụ thể trong 0–2s (VD: "
                "“3 lỗi khiến video 0 view”)."
            ),
        )
    ]


def extract_niche_hook_percentile_gap_signal(ctx: dict) -> list[Signal]:
    nm = ctx.get("niche_meta") or {}
    if not isinstance(nm, dict):
        return []
    dist = nm.get("hook_distribution")
    if not isinstance(dist, dict) or not dist:
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE_FOR_HOOK_RANK:
        return []

    total = sum(int(v or 0) for v in dist.values())
    if total <= 0:
        return []

    ha = _hook_analysis_dict(ctx)
    ht = str(ha.get("hook_type") or "").strip().lower().replace("-", "_")
    if not ht or ht in ("none", "other"):
        return []

    hook_count = int(dist.get(ht) or dist.get(ht.replace("_", "-")) or 0)
    percentile = round(100 * hook_count / total)
    if percentile >= 15:
        return []

    return [
        Signal(
            id="niche_hook_percentile_gap",
            section_id="hook_analysis",
            taxonomy_ref="§4.8.3",
            salience=0.77,
            claim=(
                f"Hook `{ht}` chỉ ~{percentile}% corpus ngách — "
                "có dấu hiệu lệch pattern hook đang tích lũy view."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"hook_type={ht} niche_hook_share={percentile}%",
                    location="user_analysis.hook_analysis+niche_meta.hook_distribution",
                )
            ],
            suggested_fix="Thử hook thuộc top 3 distribution hoặc tách biệt rõ chủ đích.",
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
    out.extend(extract_niche_hook_percentile_gap_signal(ctx))
    out.extend(extract_hook_timeline_pacing_signal(ctx))
    out.extend(extract_hook_pacing_cut_frequency_signal(ctx))
    out.extend(extract_hook_vague_specificity_signal(ctx))
    return out
