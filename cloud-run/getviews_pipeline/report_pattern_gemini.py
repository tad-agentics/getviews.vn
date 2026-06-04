"""Phase C.2.2 — optional Gemini copy for pattern reports (bounded, fallbacks).

D.2.5.b upgrade: swap manual ``json.loads`` + hand-validated dict schema
for pydantic ``response_json_schema`` binding so the parse-side mirrors
the D.1.2 Script-generate pattern. Hand-tuned per-field truncation +
padding stays identical; only the parser changes.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class PatternNarrativeLLM(BaseModel):
    """Gemini response schema for fill_pattern_narrative.

    List lengths aren't pinned at the schema level — the number of hooks
    varies per call (n_top / n_st), and the post-processing loop pads /
    truncates with deterministic fallbacks. ``cultural_framing`` is padded
    to ``n_top``; ``cross_pattern_synthesis`` is capped at 4 strings;
    ``generated_prerequisites`` has one sublist per top hook (2–4 chips each;
    empty sublists fall back to static chips in ``compute_findings``).
    """

    thesis: str = Field(default="", description="Starts with 'Kết luận nhanh:' followed by the single most specific finding with WoW numbers.")
    hook_insights: list[str] = Field(default_factory=list)
    stalled_insights: list[str] = Field(default_factory=list)
    related_questions: list[str] = Field(default_factory=list)
    cultural_framing: list[str] = Field(default_factory=list)
    cross_pattern_synthesis: list[str] = Field(default_factory=list)
    generated_prerequisites: list[list[str]] = Field(default_factory=list)
    # Narrative upgrade fields — n_top items each; empty string = no data / fallback to hook_insights
    hook_narratives: list[str] = Field(default_factory=list)
    why_it_works: list[str] = Field(default_factory=list)
    micro_patterns: list[str] = Field(default_factory=list)


def _normalize_generated_prerequisites(raw: Any, n_top: int) -> list[list[str]]:
    """Coerce Gemini output to ``n_top`` sublists of 2–4 strings; invalid → ``[]`` (static fallback)."""
    if not raw or not isinstance(raw, list):
        return [[] for _ in range(n_top)]
    out: list[list[str]] = []
    for i in range(n_top):
        if i >= len(raw) or raw[i] is None:
            out.append([])
            continue
        sub = raw[i]
        if not isinstance(sub, (list, tuple)):
            out.append([])
            continue
        chips: list[str] = []
        for x in sub:
            if x is None:
                continue
            t = str(x).strip()
            if not t:
                continue
            chips.append(t[:120])
            if len(chips) >= 4:
                break
        out.append(chips if len(chips) >= 2 else [])
    return out


def build_why_won_list(top_hook_labels: list[str]) -> list[str]:
    """Runner-up contrast: each hook vs next-ranked hook in the list."""
    out: list[str] = []
    for i, a in enumerate(top_hook_labels):
        b = top_hook_labels[i + 1] if i + 1 < len(top_hook_labels) else ""
        out.append(_fallback_why_won(a, b)[:200])
    return out


def fill_pattern_narrative(
    *,
    query: str,
    niche_label: str,
    top_hook_labels: list[str],
    stalled_hook_labels: list[str],
    live_context: str = "",
    micro_context: str = "",
    creator_counts_str: str = "",
    top_performers_str: str = "",
    ab_context: str = "",
    wow_diff: dict | None = None,
    corpus_size: int = 0,
) -> dict[str, Any]:
    """Return narrative dict for pattern synthesis (thesis, insights, questions,
    cultural_framing per hook, cross_pattern_synthesis, generated_prerequisites per hook).

    Uses Gemini JSON when ``GEMINI_API_KEY`` is available; otherwise deterministic
    Vietnamese copy grounded in labels (still bounded).
    """
    from getviews_pipeline.config import GEMINI_API_KEY

    if not GEMINI_API_KEY:
        return _fallback_narrative(query, niche_label, top_hook_labels, stalled_hook_labels)

    try:
        from google.genai import types

        from getviews_pipeline.config import GEMINI_KNOWLEDGE_FALLBACKS, GEMINI_KNOWLEDGE_MODEL
        from getviews_pipeline.gemini import (
            _generate_content_models,
            _normalize_response,
            _response_text,
        )

        n_top = len(top_hook_labels)
        n_st = len(stalled_hook_labels)
        query_clean = (query or "").strip()
        micro_inject = (micro_context or "").strip() or "(không có dữ liệu micro-element)"
        counts_inject = (creator_counts_str or "").strip() or "(không có)"
        extra_live = (live_context or "").strip()
        live_block = (
            f"\n--- BỔ SUNG LIVE (ví dụ xu hướng; không dùng để bịa aggregate) ---\n{extra_live}\n"
            if extra_live
            else ""
        )
        top_perf = (top_performers_str or "").strip() or "(không có dữ liệu)"
        performers_block = f"""
--- Top creator view cao per hook (CITE trong hook_insights; chỉ từ danh sách; "@handle (X view)") ---
{top_perf}
"""
        ab_ex = (ab_context or "").strip() or "(không tìm thấy cặp A/B)"
        ab_block = f"""
--- A/B corpus (có thể cite vào phần tóm lại tuần này hoặc thesis) ---
{ab_ex}
"""
        # AQ-1 — WoW delta injection: build block when corpus is adequate
        # and the WoW data shows a meaningful rank movement or new entry.
        wow_block = ""
        try:
            from getviews_pipeline.claim_tiers import CLAIM_TIERS

            if wow_diff and corpus_size >= CLAIM_TIERS["trend_delta"]:
                new_entries = wow_diff.get("new_entries") or []
                rank_changes = wow_diff.get("rank_changes") or []

                # Priority 1: newly appeared hook (was outside top-10 prior week)
                if new_entries:
                    top_new = new_entries[0]
                    hook_vi = top_new.get("hook_type") or ""
                    if hook_vi:
                        wow_block = (
                            f"WOW ALERT: Hook [{hook_vi}] LẦN ĐẦU vào top-10 tuần này — "
                            f"không có trong top-10 tuần trước. "
                            f"Đề cập điều này trong thesis bằng câu cụ thể.\n\n"
                        )

                # Priority 2: biggest rank climber (rank_change = rank_prior - rank_now → positive = climbed)
                elif rank_changes:
                    best = max(rank_changes, key=lambda r: abs(r.get("rank_change") or 0), default=None)
                    if best:
                        rc = best.get("rank_change") or 0
                        hook_vi = best.get("hook_type") or ""
                        # Treat rank movement >= 2 positions as notable (10-rank scale → ~20% shift)
                        if hook_vi and abs(rc) >= 2:
                            direction = "tăng" if rc > 0 else "giảm"
                            wow_block = (
                                f"WOW ALERT: Hook [{hook_vi}] {direction} {abs(rc)} bậc so với tuần trước "
                                f"(rank_prior={best.get('rank_prior')} → rank_now={best.get('rank_now')}). "
                                f"Đề cập điều này trong thesis bằng câu cụ thể.\n\n"
                            )
        except Exception:
            wow_block = ""

        has_top_performers = bool((top_performers_str or "").strip())
        hook_insights_rule = (
            f"- hook_insights: đúng {n_top} string ≤200 ký tự — fallback ngắn cho hook_narratives (dùng khi narrative rỗng). PHẢI: (1) cite ≥1 creator cụ thể từ danh sách top performer với số view thực, (2) giải thích CƠ CHẾ TÂM LÝ (không chỉ mô tả), (3) liên hệ micro-element cụ thể (framing/overlay/nhịp) từ data."
            if has_top_performers
            else f"- hook_insights: đúng {n_top} string ≤200 ký tự — fallback ngắn. Đề cập yếu tố cụ thể (framing, overlay, nhịp cắt) khi có trong dữ liệu micro-element bên dưới."
        )
        hook_narratives_rule = (
            f"- hook_narratives: đúng {n_top} string ≤500 ký tự — đoạn văn KHAI CHUYỆN cho hook đó. "
            f"CẤU TRÚC BẮT BUỘC: (1) Mở bằng '@handle' cụ thể từ danh sách top performer, kèm số view thực và "
            f"1-2 câu MÔ TẢ CẢNH QUAY CỤ THỂ: creator làm gì trong 3 giây đầu, có nhạc không, text overlay thế nào. "
            f"(2) Nếu có view chênh lệch lớn so với video khác cùng kênh, PHẢI đề cập: 'gấp Nx trung bình kênh'. "
            f"(3) Nếu còn ký tự, thêm creator thứ 2 ngắn gọn (1 câu). "
            f"Không viết chung chung. Không dùng 'hiệu quả', 'viral', 'bùng nổ'. "
            f"Ví dụ tốt: '@hagiang.makeup đăng clip cầm serum nói thẳng vào máy \"tôi dùng 30 ngày — đây là kết quả\". "
            f"Không nhạc nền, close-up da tay, text vàng trên nền đen → 233K view, gấp 4× trung bình kênh.'"
            if has_top_performers
            else f"- hook_narratives: đúng {n_top} string ≤500 ký tự — mô tả cách hook này thường được thực hiện, "
                 f"loại cảnh quay phổ biến, và tại sao format đó kéo được view. Không cần cite @handle nếu không có dữ liệu."
        )
        why_it_works_rule = (
            f"- why_it_works: đúng {n_top} string ≤350 ký tự — giải thích CƠ CHẾ TÂM LÝ hoặc VĂN HÓA khiến hook này "
            f"hiệu quả ở thị trường Việt Nam tuần này. Viết như giải thích cho người mới — không dùng jargon marketing. "
            f"Được phép so sánh với hành vi người dùng thực tế (ví dụ: 'người xem đã quen bị quảng cáo che giấu sự thật'). "
            f"Kết bằng 1 câu chỉ ra điều tạo ra sự khác biệt cụ thể (góc máy, nhịp cắt, ngôn từ, v.v.)."
        )
        micro_patterns_rule = (
            f"- micro_patterns: đúng {n_top} string — nếu trong dữ liệu top performer hoặc scene mẫu có một biến thể "
            f"CỰC KỲ CỤ THỂ đang nổi (ví dụ: creator nam gọi khán giả là 'vợ', hay creator dùng da tay không makeup để "
            f"chứng minh), hãy đặt tên và mô tả ngắn gọn ≤220 ký tự: 'Biến thể đang nổi: [tên] — [mô tả + dấu hiệu]'. "
            f"Nếu KHÔNG thấy biến thể cụ thể đủ nổi bật, để chuỗi rỗng ''. KHÔNG bịa nếu không có bằng chứng trong dữ liệu."
        )
        prompt = f"""{wow_block}Trả về DUY NHẤT một JSON object (không markdown) với các khóa:

- thesis: string ≤300 ký tự — BẮT ĐẦU BẰNG "Kết luận nhanh:" rồi 1 câu phát hiện CỤ THỂ NHẤT tuần này kèm số liệu thực. Nếu có WOW ALERT phía trên, ưu tiên đưa số đó vào câu mở (ví dụ: "Kết luận nhanh: Bằng chứng xã hội tăng 3 bậc so với tuần trước — đang là hook thắng tuyệt đối ngách {niche_label}."). Nếu không có WoW delta, mở bằng hook dẫn đầu + view trung bình cụ thể. Sau câu mở, nêu thêm 1 xu hướng bổ sung. KHÔNG bắt đầu bằng "Trong ngách..." hay câu generic.
{hook_narratives_rule}
{hook_insights_rule}
- stalled_insights: đúng {n_st} string ≤200 ký tự — vì sao hook suy liên quan câu hỏi.
- related_questions: đúng 4 string ngắn ≤80 ký tự — follow-up LIÊN TIẾP câu hỏi hiện tại.
- cultural_framing: đúng {n_top} string — QUAN TRỌNG. Mỗi string: nếu pattern này liên kết với văn hóa Việt Nam (mùa thi cử, văn hóa đám cưới, Vinglish/ngôn ngữ bản sắc, tâm lý Gen Z, thói quen tiêu dùng Shopee, v.v.), viết 1 câu giải thích TẠI SAO văn hóa đó làm hook này mạnh hơn ở VN so với thị trường khác. Câu phải cụ thể — không viết chung chung. Nếu KHÔNG có liên kết văn hóa rõ ràng với dữ liệu này, để "". Ví dụ tốt: "Văn hóa áp lực học thi ở VN khiến 'AI thầy giáo khắt khe' cộng hưởng sâu hơn với học sinh — không chỉ giải trí mà còn release tension thực sự." Ví dụ xấu: "Phù hợp với văn hóa Việt Nam."
{why_it_works_rule}
{micro_patterns_rule}
- cross_pattern_synthesis: đúng 3-4 string ≤120 ký tự — CHỦ ĐỀ XUYÊN SUỐT nhiều pattern CÙNG LÚC trong tuần này. Đây là "tóm lại tuần này" — không lặp lại insight từng hook. Mỗi string là 1 quy luật cụ thể có thể verify bằng số, ví dụ: "Text overlay vàng đang là chuẩn ngách — 4/5 video viral đều có", "Account nhỏ vẫn thắng — algorithm thưởng format, không thưởng follower count". PHẢI DỰA TRÊN dữ liệu micro-element và creator_count bên dưới.
- generated_prerequisites: đúng {n_top} sublists. Mỗi sublist: 2-4 yếu tố sản xuất CỤ THỂ và BẮT BUỘC cho hook đó, dựa trên micro-element data. KHÔNG CHUNG CHUNG.
  Tốt: ["Dưới 22 giây", "Không nhạc nền", "Filter biến dạng khuôn mặt", "Text tiếng Việt frame đầu"]
  Xấu: ["Khung hình ổn định", "Âm thanh rõ"] — quá generic, không derive từ data.
  Nếu micro-element data cho hook đó thiếu → dùng ["Khung hình 9:16", "Hook trong 1s đầu"].

--- DỮ LIỆU ĐẦU VÀO ---
Ngách: {niche_label}
Câu hỏi người dùng: "{query_clean or '(không nêu rõ — trả lời dựa trên xu hướng hook hiện tại)'}"
Hook đang thắng (xếp hạng): {top_hook_labels}
Hook suy (nếu có): {stalled_hook_labels}

Micro-element từ corpus (dùng để tăng độ cụ thể trong hook_narratives + hook_insights + cross_pattern_synthesis):
{micro_inject}

Creator count per pattern (dùng để framing cross-creator validation):
{counts_inject}
Khi creator_count >= 3: ghi rõ "pattern này giữ vững ở X creator — format là biến số, không phải creator"
{live_block}{performers_block}{ab_block}
"""
        system_instruction = (
            "Bạn là chuyên gia phân tích TikTok Việt Nam. Nhiệm vụ: trả lời user prompt bằng insight thực chiến. "
            "Trả về DUY NHẤT JSON (không markdown) đúng schema response.\n\n"
            "--- QUY TẮC ---\n"
            "NGẮN GỌN & VERDICT-FIRST — BẮT BUỘC: mỗi hook mở bằng 1 câu verdict in đậm; toàn báo cáo ~350-450 từ. "
            "KHÔNG đánh giá giờ đăng / khung giờ vàng.\n"
            "- Tiếng Việt tự nhiên, không emoji, không mở đầu \"Chào bạn\".\n"
            "- Không dùng: \"chắc chắn\", \"hiệu quả\", \"bùng nổ\", \"công thức vàng\".\n"
            "- Số liệu chỉ được trích từ dữ liệu trong user prompt; không tự bịa ra %.\n"
            "- hook_narratives là trường ưu tiên — viết đủ 500 ký tự nếu có dữ liệu. "
            "hook_insights chỉ là fallback ngắn.\n"
            "- cultural_framing, why_it_works, micro_patterns, cross_pattern_synthesis — "
            "không bỏ qua bất kỳ trường nào.\n"
            f"- generated_prerequisites: bắt buộc đủ {n_top} sublist theo user prompt "
            "(có thể rỗng [] nếu không infer được — khi đó backend dùng chip mặc định theo hook).\n"
            "- Khi phần Micro-element trong user prompt chỉ là đúng "
            "\"(không có dữ liệu micro-element)\", KHÔNG đưa số liệu hoặc chi tiết cụ thể "
            "về micro-element; không bịa micro-pattern.\n"
        )
        cfg = types.GenerateContentConfig(
            temperature=0.35,
            max_output_tokens=3500,
            response_mime_type="application/json",
            response_json_schema=PatternNarrativeLLM.model_json_schema(),
            system_instruction=system_instruction,
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
            call_site="pattern_narrative",
        )
        raw = _response_text(resp)
        try:
            data = PatternNarrativeLLM.model_validate_json(_normalize_response(raw))
        except ValidationError as exc:
            logger.warning("[pattern] Gemini narrative schema mismatch: %s — fallback", exc)
            return _fallback_narrative(query, niche_label, top_hook_labels, stalled_hook_labels)
        thesis = data.thesis[:300]
        hi = [s[:200] for s in data.hook_insights]
        si = [s[:200] for s in data.stalled_insights]
        rq = [s[:80] for s in data.related_questions][:4]
        cf = [s[:300] for s in data.cultural_framing]
        cps = [s[:120] for s in data.cross_pattern_synthesis][:4]
        while len(hi) < n_top:
            hi.append(_fallback_insight(top_hook_labels[len(hi)]))
        while len(si) < n_st:
            si.append(_fallback_stalled(stalled_hook_labels[len(si)]))
        while len(rq) < 4:
            rq.append(f"Xu hướng nào đang nổi trong {niche_label}?")
        while len(cf) < n_top:
            cf.append("")
        cf = cf[:n_top]
        gp = _normalize_generated_prerequisites(data.generated_prerequisites, n_top)

        # Narrative upgrade fields
        raw_narratives = list(data.hook_narratives or [])
        raw_why = list(data.why_it_works or [])
        raw_micro = list(data.micro_patterns or [])
        hook_narratives = [s[:500] for s in raw_narratives]
        why_it_works_list = [s[:350] for s in raw_why]
        micro_patterns_list = [s[:220] for s in raw_micro]
        while len(hook_narratives) < n_top:
            hook_narratives.append("")
        while len(why_it_works_list) < n_top:
            why_it_works_list.append("")
        while len(micro_patterns_list) < n_top:
            micro_patterns_list.append("")

        return {
            "thesis": thesis or _fallback_thesis(niche_label, top_hook_labels),
            "hook_insights": hi[:n_top],
            "hook_narratives": hook_narratives[:n_top],
            "why_it_works": why_it_works_list[:n_top],
            "micro_patterns": micro_patterns_list[:n_top],
            "stalled_insights": si[:n_st],
            "related_questions": rq[:4],
            "cultural_framing": cf[:n_top],
            "cross_pattern_synthesis": cps,
            "generated_prerequisites": gp,
        }
    except Exception as exc:
        logger.warning("[pattern] Gemini narrative failed: %s — fallback", exc)
        return _fallback_narrative(query, niche_label, top_hook_labels, stalled_hook_labels)


def _fallback_thesis(niche_label: str, hooks: list[str]) -> str:
    h = hooks[0] if hooks else "hook đang dẫn đầu"
    extra = f", {hooks[1]}" if len(hooks) > 1 else ""
    return f"Kết luận nhanh: {h}{extra} đang mang lại tín hiệu xem ổn định trong {niche_label} — cao hơn baseline ngách."


def _fallback_insight(label: str) -> str:
    return f"{label} giữ được retention tốt hơn trung vị — phù hợp để test trong 3 video tiếp theo."


def _fallback_stalled(label: str) -> str:
    return f"{label} đang tụt retention; cân nhắc giảm tần suất hoặc đổi hook mở đầu."


def _fallback_why_won(a: str, b: str) -> str:
    if not b:
        return f"{a} khớp với xu hướng xem hiện tại trong ngách."
    return f"{a} bám sát tốc độ tăng view tốt hơn {b} trong cùng cửa sổ."


def _fallback_narrative(
    query: str,
    niche_label: str,
    top_hook_labels: list[str],
    stalled_hook_labels: list[str],
) -> dict[str, Any]:
    thesis = _fallback_thesis(niche_label, top_hook_labels)
    if query:
        thesis = (thesis + f" (Gợi ý từ câu hỏi: {query[:80]})")[:280]
    hi = [_fallback_insight(h) for h in top_hook_labels]
    si = [_fallback_stalled(h) for h in stalled_hook_labels]
    # BUG-16 (QA audit 2026-04-22): English loan words like "oversaturated"
    # + "breakout" were leaking into the Vietnamese related-questions rail.
    # Replaced with native Vietnamese equivalents so the fallback (used
    # whenever Gemini disagrees / times out) matches the rest of the UI.
    rq = [
        f"Hook nào đang giảm tốc trong {niche_label}?",
        "Format nào đang bão hoà quá mức?",
        "Nên thử hook mới hay tối ưu hook cũ?",
        "Ngách con nào đang bứt phá tuần này?",
    ]
    return {
        "thesis": thesis,
        "hook_insights": hi,
        "hook_narratives": [""] * len(top_hook_labels),
        "why_it_works": [""] * len(top_hook_labels),
        "micro_patterns": [""] * len(top_hook_labels),
        "stalled_insights": si,
        "related_questions": rq,
        "cultural_framing": [""] * len(top_hook_labels),
        "cross_pattern_synthesis": [],
        "generated_prerequisites": [],
    }
