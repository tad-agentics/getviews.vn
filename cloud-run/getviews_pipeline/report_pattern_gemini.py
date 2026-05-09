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

    thesis: str = Field(default="")
    hook_insights: list[str] = Field(default_factory=list)
    stalled_insights: list[str] = Field(default_factory=list)
    related_questions: list[str] = Field(default_factory=list)
    cultural_framing: list[str] = Field(default_factory=list)
    cross_pattern_synthesis: list[str] = Field(default_factory=list)
    generated_prerequisites: list[list[str]] = Field(default_factory=list)


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
            f"- hook_insights: đúng {n_top} string ≤200 ký tự — mỗi string PHẢI: (1) cite ≥1 creator cụ thể từ danh sách top performer với số view thực, (2) giải thích CƠ CHẾ TÂM LÝ (không chỉ mô tả), (3) liên hệ micro-element cụ thể (framing/overlay/nhịp) từ data. Ví dụ tốt: '@kimthichnhacua (333K view) — cận cảnh tay bóp serum 0-3s + không nhạc + text vàng → trigger FOMO từ visual chi tiết.' Ví dụ xấu: 'Hook này có retention tốt vì phù hợp với người xem.'"
            if has_top_performers
            else f"- hook_insights: đúng {n_top} string ≤200 ký tự — vì sao hook đó trả lời câu hỏi. PHẢI đề cập yếu tố cụ thể (framing, overlay, nhịp cắt) khi có trong dữ liệu micro-element bên dưới (khi không có khối top performer, không bắt buộc cite @handle)."
        )
        prompt = f"""{wow_block}Bạn là chuyên gia phân tích TikTok Việt Nam. Nhiệm vụ: TRẢ LỜI câu hỏi dưới đây bằng insight thực chiến.

Trả về DUY NHẤT một JSON object (không markdown) với các khóa:

- thesis: string ≤280 ký tự — BẮT ĐẦU BẰNG: '{len(top_hook_labels)} hook đang dẫn đầu ngách {niche_label} tuần này:' rồi nêu 1-2 câu tóm tắt xu hướng lớn nhất và kết bằng bằng chứng số. KHÔNG mở đầu bằng 'Trong ngách...' hay câu generic.
{hook_insights_rule}
- stalled_insights: đúng {n_st} string ≤200 ký tự — vì sao hook suy liên quan câu hỏi.
- related_questions: đúng 4 string ngắn ≤80 ký tự — follow-up LIÊN TIẾP câu hỏi hiện tại.
- cultural_framing: đúng {n_top} string — QUAN TRỌNG. Mỗi string: nếu pattern này liên kết với văn hóa Việt Nam (mùa thi cử, văn hóa đám cưới, Vinglish/ngôn ngữ bản sắc, tâm lý Gen Z, thói quen tiêu dùng Shopee, v.v.), viết 1 câu giải thích TẠI SAO văn hóa đó làm hook này mạnh hơn ở VN so với thị trường khác. Câu phải cụ thể — không viết chung chung. Nếu KHÔNG có liên kết văn hóa rõ ràng với dữ liệu này, để "". Ví dụ tốt: "Văn hóa áp lực học thi ở VN khiến 'AI thầy giáo khắt khe' cộng hưởng sâu hơn với học sinh — không chỉ giải trí mà còn release tension thực sự." Ví dụ xấu: "Phù hợp với văn hóa Việt Nam."
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

Micro-element từ corpus (dùng để tăng độ cụ thể trong hook_insights + cross_pattern_synthesis):
{micro_inject}

Creator count per pattern (dùng để framing cross-creator validation):
{counts_inject}
Khi creator_count >= 3: ghi rõ "pattern này giữ vững ở X creator — format là biến số, không phải creator"
{live_block}{performers_block}{ab_block}

--- QUY TẮC ---
- Tiếng Việt tự nhiên, không emoji, không mở đầu "Chào bạn".
- Không dùng: "chắc chắn", "hiệu quả", "bùng nổ", "công thức vàng".
- Số liệu chỉ được trích từ dữ liệu trên; không tự bịa ra %.
- cultural_framing và cross_pattern_synthesis là 2 trường MỚI — không bỏ qua.
- generated_prerequisites: bắt buộc đủ {n_top} sublist (có thể rỗng [] nếu không infer được — khi đó backend dùng chip mặc định theo hook).
"""
        cfg = types.GenerateContentConfig(
            temperature=0.35,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_json_schema=PatternNarrativeLLM.model_json_schema(),
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        raw = _response_text(resp)
        try:
            data = PatternNarrativeLLM.model_validate_json(_normalize_response(raw))
        except ValidationError as exc:
            logger.warning("[pattern] Gemini narrative schema mismatch: %s — fallback", exc)
            return _fallback_narrative(query, niche_label, top_hook_labels, stalled_hook_labels)
        thesis = data.thesis[:280]
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
        return {
            "thesis": thesis or _fallback_thesis(niche_label, top_hook_labels),
            "hook_insights": hi[:n_top],
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
    h = ", ".join(hooks[:3]) if hooks else "các hook đang được ưa chuộng"
    return f"Trong {niche_label}, {h} đang mang lại tín hiệu xem ổn định so với baseline ngách."


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
        "stalled_insights": si,
        "related_questions": rq,
        "cultural_framing": [""] * len(top_hook_labels),
        "cross_pattern_synthesis": [],
        "generated_prerequisites": [],
    }
