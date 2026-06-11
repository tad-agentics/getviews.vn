from __future__ import annotations

import json
from typing import Any

from getviews_pipeline.diagnose_sections import default_section_title
from getviews_pipeline.signals.base import Signal

DIAGNOSIS_V6_JSON_INSTRUCTION = """
Sau phần hướng dẫn, bạn nhận DIAGNOSTIC_CONTEXT (JSON) + SECTIONS_TO_EMIT + SIGNAL_MANIFEST.

Output BẮT BUỘC — đúng một khối fence đầu tiên:

```json
{
  "diagnosis_vi": {
    "headline_vi": "một câu ≤16 từ — verdict dứt khoát + đòn bẩy lớn nhất (KHÔNG kiểu 'tốt nhưng cần tối ưu')",
    "sections": [
      {
        "section_id": "<id>",
        "title": "tiêu đề tiếng Việt — câu thường (chữ đầu viết hoa), KHÔNG viết hoa toàn bộ; dùng DEFAULT_TITLES_HINT khi có",
        "text": "MỘT câu verdict in đậm (**...**) là kết luận section — đọc riêng câu này là đủ hiểu. Sau đó TỐI ĐA 2 câu chứng minh bằng số/dữ liệu kênh. KHÔNG quá 50 từ. KHÔNG viết đoạn 150-200 từ.",
        "findings": [
          {
            "title_vi": "Tên vấn đề — hậu quả, ≤10 từ",
            "body_vi": "1 câu + số liệu cụ thể (X views, Y% mẫu)",
            "fix_vi": "1 hành động copy-paste được creator làm ngay (hook template, con số, thao tác)"
          }
        ],
        "embedded_tiles": [
          {"aweme_id": "<id từ REFERENCE_EVIDENCE>", "narrative_vi": "1-3 câu: vì sao chọn video này + nó làm tốt điều gì (hook, format, nhịp) so với clip đang phân tích"}
        ],
        "next_video": null
      }
    ],
    "evidence_anchors": [
      {"signal_id": "...", "section_id": "...", "type": "user_analysis_field|aweme_id|niche_norms_pct|channel_field", "quote": "...", "location": null}
    ]
  },
  "format_cards": []
}
```

Quy tắc:

ĐỘ DÀI & CẤU TRÚC (ưu tiên cao nhất — audience là creator, đọc lướt trên mobile):
- TỔNG báo cáo ~350-450 từ. Mỗi section.text: 1 câu verdict in đậm + tối đa 2 câu chứng minh (≤50 từ). KHÔNG đoạn 150-200 từ, KHÔNG section nào dài hơn 3 câu prose.
- VERDICT-FIRST: câu đầu mỗi section là kết luận in đậm — đọc các câu đậm xuyên suốt bài là hiểu toàn bộ. Phần còn lại chỉ chứng minh + fix + reference.
- ĐƠN VỊ CHÍNH là FINDINGS + REFERENCE, KHÔNG phải prose. Khi phân vân giữa viết thêm 1 đoạn giải thích và đưa thêm 1 finding/1 reference tile → luôn chọn finding/reference. Prose chỉ là 1 câu verdict dẫn vào.
- DẠY VIỆC CẦN LÀM > chẩn đoán. Nén chẩn đoán còn 1 câu; dồn không gian cho fix cụ thể, reference video, và script clip tiếp theo.
- Chỉ tạo các section có trong SECTIONS_TO_EMIT, đúng thứ tự đó. KHÔNG tạo section timing/giờ đăng/distribution dù có data — giờ đăng không phải yếu tố xếp hạng.

FINDINGS (đơn vị hiển thị chính của section issue-based):
- Section issue-based (diagnosis, hook_analysis, compliance, sound, editing, metadata, script_structure): 2-3 findings — đây là phần creator đọc kỹ nhất. Mỗi finding: title_vi (≤10 từ, "Vấn đề — hậu quả"), body_vi (1 câu + số liệu), fix_vi (1 hành động copy-paste: hook template, con số, thao tác cụ thể — KHÔNG "cải thiện hook").
- KHÔNG tạo finding về tiết lộ thương mại / #qc / #ad / Luật Quảng cáo disclosure — ngoài phạm vi sản phẩm video diagnosis.
- Section không issue-based (next_video, niche_pattern, channel_pattern, douyin_origin, persona): findings: [].
- Số liệu inline dạng (234K views), (62% mẫu 380) — giải thích ý nghĩa trong cùng câu.
- CHỐNG pad: mỗi câu advance argument; không lặp ý. evidence_anchors khớp claim trong text.

REFERENCE TILES (làm bằng chứng nổi bật — không chôn trong prose):
- Section show được trực quan (niche_pattern, diagnosis, hook_analysis, script_structure): điền tối đa **3** embedded_tiles **khác aweme_id** từ REFERENCE_EVIDENCE. niche_pattern ưu tiên đủ 3 tile — đây là lưới "top ngách đang làm gì", reference là nhân vật chính, prose dẫn vào chỉ 1 câu.
- Mỗi aweme_id chỉ dùng ở MỘT section. narrative_vi = 1 câu (tối đa 2) **khác nhau cho từng video**: nêu **điều cần copy** (hook/format/nhịp cụ thể) so với clip đang phân tích. Góc theo section (hook_analysis → 3 giây đầu; diagnosis/niche_pattern → format/hiệu quả). KHÔNG nhắc @handle hay số view (card đã hiển thị). KHÔNG lặp narrative_vi vào text. Tuân thủ ADDRESSING_MODE trong DIAGNOSTIC_CONTEXT.
- Chỉ chọn video gần context (CTX_SUMMARY). Không đủ peer phù hợp → ít tile hơn hoặc [].
- Section phân tích thuần (channel_pattern, persona, compliance): tile tùy chọn, không bắt buộc.

CHANNEL_PATTERN (Ref-style: kênh tự chứng minh):
- Dùng channel_context: trích số cụ thể (top video X views, bottom Y views, mức view thường của kênh). 1 câu verdict in đậm: video này so với mức thường của kênh thế nào + creator nên nhân đôi cái gì. Tối đa 2 câu. Nếu source="live": ghi chú nhẹ dữ liệu kênh là live.

NEXT_VIDEO (script copy-paste được, KHÔNG concept trừu tượng):
- next_video là object { "hook_vi", "premise_vi", "format", "reason_vi", "expected_views_range" }; findings: [].
- text của section = script theo cảnh, mỗi dòng 1 bullet •: "• Hook (0-1s): [câu copy-paste]" → "• Beat 2: ..." → "• Beat 3: ..." → "• CTA: ...". Creator phải quay được ngay mà không cần nghĩ thêm.

NICHE_PATTERN:
- embedded_tiles từ reference pool (ưu tiên đủ 3); findings: []. Nếu có cross_format_signal: 1 câu verdict in đậm — "format X đang chạy ở N ngách / hook nào đạt view cao nhất" + creator học gì. Phải ra conclusion, không chỉ mô tả.
- Ngôn ngữ: tiếng Việt peer-to-peer. Dùng **view** (không "lượt xem"), **tỷ lệ tương tác** (không "engagement rate"). Tránh quote tiếng Anh thô — diễn đạt format/hook bằng tiếng Việt. Khi performance_tier=hit: khung breakout, hook chỉ là polish — không mô tả như flop.
"""

DIAGNOSIS_V6_SHORTEN_RETRY_APPEND = """
BẮT BUỘC RÚT GỌN (lần 2): Bản trước quá dài. Trả lại JSON đầy đủ cùng schema.
- TỔNG ≤450 từ (mọi section.text + findings).
- Mỗi section.text (trừ next_video): ≤50 từ — 1 verdict **in đậm** + tối đa 2 câu chứng minh.
- Giữ đủ findings (2-3/issue section) và embedded_tiles; cắt prose thừa, KHÔNG bỏ fix_vi.
- next_video: giữ bullet script • Hook → Beat → CTA, gọn hơn nếu cần.
"""


def _signal_payload(manifest_trim: dict[str, list[Signal]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sid, sigs in sorted(manifest_trim.items(), key=lambda x: x[0]):
        for s in sigs:
            rows.append(
                {
                    "section_id": sid,
                    "signal_id": s.id,
                    "salience": round(s.salience, 3),
                    "taxonomy_ref": s.taxonomy_ref,
                    "claim": s.claim,
                    "evidence": [
                        {"type": e.type, "quote": e.quote, "location": e.location}
                        for e in s.evidence
                    ],
                    "suggested_fix": s.suggested_fix,
                }
            )
    return rows


def _trim_channel_context(cc: dict[str, Any] | None) -> dict[str, Any]:
    """Return a compact channel_context payload safe to embed in the Gemini prompt.

    Includes only the fields Gemini needs to write a meaningful channel_pattern
    narrative: top/bottom video views + format, median_views, best_performing_format,
    per_format_views summary, and sample_size.  Strips large blobs (tiktok_url,
    aweme_id, raw desc beyond a short snippet) to keep token cost low.
    """
    if not cc or not cc.get("available"):
        return {"available": False}

    def _trim_video(v: dict[str, Any]) -> dict[str, Any]:
        return {
            "views": v.get("views"),
            "content_format": v.get("content_format"),
            "desc_snippet": str(v.get("desc") or "")[:80],
        }

    out: dict[str, Any] = {
        "available": True,
        "source": cc.get("source", "corpus"),  # "corpus" or "live" (ED fallback)
        "sample_size": cc.get("sample_size"),
        "median_views": cc.get("median_views"),
        "best_performing_format": cc.get("best_performing_format"),
        "performance_tier": cc.get("performance_tier"),
    }
    top = cc.get("top_videos") or []
    bottom = cc.get("bottom_videos") or []
    if top:
        out["top_videos"] = [_trim_video(v) for v in top[:2]]
    if bottom:
        out["bottom_videos"] = [_trim_video(v) for v in bottom[:2]]
    pf = cc.get("per_format_views")
    if isinstance(pf, dict):
        # Summarise per-format: just avg_views + count, sorted by avg_views desc
        pf_trim = {
            fmt: {"avg_views": vals.get("avg_views"), "n": vals.get("n") or vals.get("count")}
            for fmt, vals in pf.items()
            if isinstance(vals, dict)
        }
        if pf_trim:
            out["per_format_views"] = pf_trim
    return out


_DIGEST_TRANSCRIPT_CHARS = 420
_DIGEST_MAX_SCENES = 8
# Heavy raw keys the digest replaces — everything else in user_analysis is
# scalar/small and passes through whole (the old ``[:24]`` key cliff silently
# dropped scene grammar, audio fields and the hook timeline; quality audit
# 2026-06-11).
_DIGEST_RAW_KEYS = frozenset({"scenes", "audio_transcript", "key_timestamps", "hook_timeline"})


def build_user_evidence_digest(user_analysis: dict[str, Any]) -> dict[str, Any]:
    """Synthesize the heavy extraction arrays into a compact evidence digest.

    Design constraint (CEO direction 2026-06-11): this data must DEEPEN the
    existing findings, not spawn new report topics — so it's compressed into
    a few dense lines the synthesis can cite (timestamps, spoken lines,
    scene grammar) inside the sections it already writes.
    """
    digest: dict[str, Any] = {}

    # Hook timeline → one ordered line: "face_enter 0.2s → first_word 0.5s → text 0.9s"
    # Schema home is hook_analysis.hook_timeline (models.py HookAnalysis);
    # the top-level fallback covers normalised payloads that hoist it.
    hook_block = user_analysis.get("hook_analysis")
    timeline = (
        hook_block.get("hook_timeline") if isinstance(hook_block, dict) else None
    ) or user_analysis.get("hook_timeline")
    if isinstance(timeline, list) and timeline:
        steps = []
        for ev in timeline[:6]:
            if not isinstance(ev, dict):
                continue
            label = str(ev.get("event") or ev.get("type") or "?")
            t = ev.get("t") if ev.get("t") is not None else ev.get("at_s")
            try:
                steps.append(f"{label} {float(t):.1f}s")
            except (TypeError, ValueError):
                steps.append(label)
        if steps:
            digest["hook_timeline"] = " → ".join(steps)

    # Scene grammar → one line per scene: "0.0–2.5s close_up/fast/bold_center: desc"
    scenes = user_analysis.get("scenes")
    if isinstance(scenes, list) and scenes:
        scene_lines: list[str] = []
        for sc in scenes[:_DIGEST_MAX_SCENES]:
            if not isinstance(sc, dict):
                continue
            t0, t1 = sc.get("start_s"), sc.get("end_s")
            try:
                span = f"{float(t0):.1f}–{float(t1):.1f}s"
            except (TypeError, ValueError):
                span = "?"
            dims = "/".join(
                str(sc.get(k)) for k in ("framing", "pace", "overlay_style") if sc.get(k)
            )
            desc = str(sc.get("description") or "")[:60]
            scene_lines.append(f"{span} {dims}: {desc}".strip())
        if scene_lines:
            digest["scene_pattern"] = scene_lines
        if len(scenes) > _DIGEST_MAX_SCENES:
            digest["scene_pattern_note"] = f"({len(scenes)} cảnh, hiển thị {_DIGEST_MAX_SCENES} đầu)"

    # What the creator actually SAID — the opening matters most.
    transcript = str(user_analysis.get("audio_transcript") or "").strip()
    if transcript:
        digest["transcript_opening"] = transcript[:_DIGEST_TRANSCRIPT_CHARS] + (
            "…" if len(transcript) > _DIGEST_TRANSCRIPT_CHARS else ""
        )

    # Audio character — one compact line, not a new section.
    audio_bits = [
        str(user_analysis.get(k))
        for k in ("audio_track_role", "sound_layering")
        if user_analysis.get(k)
    ]
    if audio_bits:
        digest["audio_character"] = " · ".join(audio_bits)

    return digest


def build_diagnosis_v6_user_prompt(
    *,
    sections_to_emit: list[str],
    manifest_for_llm: dict[str, list[Signal]],
    ctx: dict[str, Any],
    content_format: str,
    niche_name: str,
    corpus_size: int,
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    performance_tier: str,
    channel_context: dict[str, Any] | None,
    errors: list[dict[str, Any]] | None,
    wants_directions: bool,
    corpus_citation: str = "",
    persona_block: str = "",
    reference_evidence_block: str = "",
    niche_posting_context_block: str = "",
    collapsed_questions: list[str] | None = None,
    cross_format_signal: dict[str, Any] | None = None,
    addressing_mode: str = "third_party",
    video_creator_handle: str | None = None,
) -> str:
    tier = str(performance_tier or "unknown").lower()
    default_titles = {
        sid: default_section_title(sid, tier) for sid in sections_to_emit
    }
    cross_format_trim: dict[str, Any] | None = None
    if cross_format_signal and isinstance(cross_format_signal, dict):
        cross_format_trim = {
            "format_label_vi": cross_format_signal.get("format_label_vi"),
            "niches_with_format": cross_format_signal.get("niches_with_format"),
            "top_hooks": [
                {
                    "hook_type_vi": h.get("hook_type_vi"),
                    "avg_views": h.get("avg_views"),
                    "niche_count": h.get("niche_count"),
                }
                for h in (cross_format_signal.get("top_hooks") or [])[:3]
            ],
        }
    payload = {
        "SECTIONS_TO_EMIT": sections_to_emit,
        "DEFAULT_TITLES_HINT": default_titles,
        "SIGNAL_MANIFEST": _signal_payload(manifest_for_llm),
        "CTX_SUMMARY": {
            "niche_name": niche_name,
            "content_format": content_format,
            "corpus_size": corpus_size,
            "performance_tier": performance_tier,
            "addressing_mode": addressing_mode,
            "video_creator_handle": (video_creator_handle or "").strip().lstrip("@") or None,
        },
        "user_stats_trim": {
            k: user_stats.get(k)
            for k in ("caption", "views", "hashtags", "music_origin", "duration_sec")
            if k in user_stats
        },
        "reference_video_ids": [
            str(r.get("aweme_id") or r.get("video_id") or "")
            for r in (reference_videos or [])[:8]
        ],
        "channel_context": _trim_channel_context(channel_context),
        "cross_format_signal": cross_format_trim,
        "errors_head": (errors or [])[:3],
        "USER_EVIDENCE_DIGEST": build_user_evidence_digest(user_analysis),
    }
    # Honesty gate: the retention curve is heuristic until real telemetry
    # exists — the synthesis must never present it as a measurement.
    if str(user_stats.get("retention_source") or "").lower() == "modeled":
        payload["retention_note"] = (
            "Retention/giữ chân là ƯỚC TÍNH theo mô hình, KHÔNG phải số đo thực. "
            "Khi nhắc retention phải kèm 'ước tính' và không dùng làm bằng chứng chính."
        )
    from getviews_pipeline.analysis_addressing import (
        AddressingMode,
        build_addressing_prompt_block,
    )

    mode: AddressingMode = (
        "viewer_own" if addressing_mode == "viewer_own" else "third_party"
    )
    addressing_block = build_addressing_prompt_block(
        mode,
        creator_handle=video_creator_handle,
    )

    blocks = [
        DIAGNOSIS_V6_JSON_INSTRUCTION.strip(),
        f"\n\n{addressing_block}\n",
        "\nDIAGNOSTIC_CONTEXT_JSON:\n",
        json.dumps(payload, ensure_ascii=False, indent=2),
        # Full scalar surface of the extraction. The heavy arrays
        # (scenes, transcript, hook_timeline) ride compressed inside
        # USER_EVIDENCE_DIGEST above — the old ``[:24]`` key cliff here
        # silently dropped them whole (quality audit 2026-06-11).
        "\n\nUSER_ANALYSIS_JSON:\n",
        json.dumps(
            {k: v for k, v in user_analysis.items() if k not in _DIGEST_RAW_KEYS},
            ensure_ascii=False,
        ),
    ]
    if corpus_citation:
        blocks.append(f"\n\nKHO_VIDEO_CITATION_BLOCK:\n{corpus_citation}")
    if persona_block:
        blocks.append(f"\n\nPERSONA_BLOCK:\n{persona_block}")
    if reference_evidence_block:
        blocks.append(f"\n\nREFERENCE_EVIDENCE:\n{reference_evidence_block}")
    if wants_directions:
        blocks.append(
            "\n\nBổ sung sau diagnosis_vi: trong format_cards để 1-4 gợi ý hướng "
            "nội dung ngắn (field tương thích FE hiện tại)."
        )
    if collapsed_questions:
        blocks.append(
            "\n\nNgười dùng hỏi nhiều câu — trả lời lồng trong sections phù hợp:\n"
            + "\n".join(f"- {q}" for q in collapsed_questions)
        )
    from getviews_pipeline.video_report_coherence import tier_implies_win_framing

    tier_note = ""
    try:
        tvr_prompt = float(user_stats["target_vs_creator_median"])
    except (KeyError, TypeError, ValueError):
        tvr_prompt = None
    try:
        cmv_prompt = int(user_stats["creator_median_views"])
    except (KeyError, TypeError, ValueError):
        cmv_prompt = None
    try:
        views_prompt = int(user_stats.get("views") or 0)
    except (TypeError, ValueError):
        views_prompt = 0
    if tier_implies_win_framing(
        tier,
        views=views_prompt,
        creator_median_views=cmv_prompt,
        target_vs_creator_median=tvr_prompt,
    ):
        tier_note = (
            "\n\nLƯU Ý video đang breakout/thắng (performance_tier hoặc so với kênh ≥2×): "
            "headline_vi và diagnosis phải khẳng định thắng — chỉ nêu hook/cắt hình như polish, "
            "không viết như video flop; dùng **view**, **tỷ lệ tương tác**."
        )
    blocks.append(
        "\n\nViết JSON đầy đủ theo schema. Mỗi section.text: 1 câu verdict in đậm + tối đa 2 câu "
        "chứng minh (≤50 từ). Tổng báo cáo ~350-450 từ. Ưu tiên fix + reference video hơn giải "
        "thích dài. KHÔNG tạo section timing/giờ đăng. Mỗi câu phải advance argument."
        "\n\nQUY TẮC ĐỘ SÂU (bắt buộc):"
        "\n- GIỮ NGUYÊN danh sách section trong SECTIONS_TO_EMIT — USER_EVIDENCE_DIGEST "
        "dùng để LÀM SÂU các nhận định sẵn có, KHÔNG mở chủ đề/section mới."
        "\n- Mỗi finding phải neo vào bằng chứng cụ thể từ digest: mốc thời gian / cảnh "
        "(scene_pattern), hoặc trích nguyên văn lời thoại (transcript_opening) khi liên quan."
        "\n- Khi REFERENCE_EVIDENCE có hook/lời mở: so sánh trực tiếp — 'bạn mở bằng X, "
        "@handle mở bằng \"Y\" (views)' — và viết fix theo dạng 'làm như @handle: <hành động>'. "
        "Người xem cần THẤY cách người thật làm, không chỉ đọc lời khuyên."
        "\n\nKỶ LUẬT CÂU (bắt buộc):"
        "\n- Câu ngắn, tuyên bố thẳng, mỗi câu đúng một ý. Mỗi câu phải mang số liệu, "
        "mốc thời gian, hoặc tên video/creator cụ thể — câu không có bằng chứng thì cắt."
        "\n- CẤM câu đệm: 'có thể thấy rằng', 'nhìn chung', 'điều này cho thấy', "
        "'một điều đáng chú ý là'. Verdict trước, bằng chứng ngay sau."
        "\n- Nhịp đúng: 'Video dừng ở 64K — bằng 35% median kênh. 3 giây đầu là cảnh tĩnh. "
        "@handle cùng ngách mở bằng chuyển động + 1 câu hỏi và đạt 1.9M.'"
        + tier_note
    )
    return "".join(blocks)
