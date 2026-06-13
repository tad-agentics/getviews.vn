from __future__ import annotations

import json
from typing import Any

from getviews_pipeline.diagnose_sections import default_section_title
from getviews_pipeline.enum_labels_vi import hook_timeline_event_vi, overlay_style_vi
from getviews_pipeline.signals.base import Signal


def _humanize_code(value: str) -> str:
    """``close_up`` → ``close up`` — readable fallback for unmapped enum codes."""
    return " ".join(str(value or "").replace("_", " ").replace("-", " ").split())

DIAGNOSIS_V6_JSON_INSTRUCTION = """
Sau phần hướng dẫn, bạn nhận DIAGNOSTIC_CONTEXT (JSON) + SECTIONS_TO_EMIT + SIGNAL_MANIFEST.

Output BẮT BUỘC — đúng một khối fence đầu tiên:

```json
{
  "diagnosis_vi": {
    "headline_vi": "một câu ≤16 từ — verdict dứt khoát + đòn bẩy lớn nhất, gọi đúng CƠ CHẾ kèm mốc giây khi evidence có («0-3s không có người nói») — KHÔNG triệu chứng chung («hook yếu»), KHÔNG kiểu 'tốt nhưng cần tối ưu', KHÔNG dùng ** hay markdown trong headline_vi; khi nêu bội số phải nói rõ chuẩn nào — «so với TB format ngách» hoặc «so với mức thường của kênh» — không nói trống «mức view thường»",
    "sections": [
      {
        "section_id": "<id>",
        "title": "tiêu đề tiếng Việt — câu thường (chữ đầu viết hoa), KHÔNG viết hoa toàn bộ; dùng DEFAULT_TITLES_HINT khi có",
        "text": "MỘT câu verdict in đậm (**...**) là kết luận section — đọc riêng câu này là đủ hiểu. Sau đó tối đa 4 câu chứng minh bằng số/dữ liệu kênh. KHÔNG quá 90 từ. KHÔNG viết đoạn 150-200 từ.",
        "findings": [
          {
            "title_vi": "Tên vấn đề — hậu quả, ≤10 từ",
            "body_vi": "1 câu + số liệu cụ thể (X views, Y% mẫu)",
            "fix_vi": "1 hành động copy-paste được creator làm ngay (hook template, con số, thao tác)",
            "evidence_ref": {"start_sec": 0.0, "end_sec": 3.0, "label_vi": "khoảnh khắc trong clip (≤6 từ)"}
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
- TỔNG báo cáo ~350-450 từ. Mỗi section.text: 1 câu verdict in đậm + tối đa 4 câu chứng minh (≤90 từ; script_structure ≤100 từ). KHÔNG đoạn 150-200 từ, KHÔNG section nào dài hơn 5 câu prose.
- VERDICT-FIRST: câu đầu mỗi section là kết luận in đậm — đọc các câu đậm xuyên suốt bài là hiểu toàn bộ. Phần còn lại chỉ chứng minh + fix + reference.
- ĐƠN VỊ CHÍNH là FINDINGS + REFERENCE, KHÔNG phải prose. Khi phân vân giữa viết thêm 1 đoạn giải thích và đưa thêm 1 finding/1 reference tile → luôn chọn finding/reference. Prose chỉ là 1 câu verdict dẫn vào.
- DẠY VIỆC CẦN LÀM > chẩn đoán. Nén chẩn đoán còn 1 câu; dồn không gian cho fix cụ thể, reference video, và script clip tiếp theo.
- Chỉ tạo các section có trong SECTIONS_TO_EMIT, đúng thứ tự đó. KHÔNG tạo section riêng cho timing/giờ đăng. Khi `user_stats_trim.stats_history` có ≥2 mốc (t0/t6h/t24h), diễn giải trong section `metadata`: view/ER tăng hay đứng, `distribution_shape=spike_then_flat` nghĩa gì, tốt/chưa tốt và 1 fix cụ thể — không chỉ liệt kê số.

FINDINGS (đơn vị hiển thị chính của section issue-based):
- Section issue-based (diagnosis, hook_analysis, compliance, sound, editing, metadata, script_structure, commerce): 2-3 findings — đây là phần creator đọc kỹ nhất. Mỗi finding: title_vi (≤10 từ, "Vấn đề — hậu quả"), body_vi (1 câu + số liệu), fix_vi (1 hành động copy-paste: hook template, con số, thao tác cụ thể — KHÔNG "cải thiện hook").
- BÁM SIGNAL_MANIFEST: salience (0-1) là độ quan trọng đã đo — findings của mỗi section viết từ các signal salience CAO NHẤT của section đó, không chọn signal yếu khi còn signal mạnh chưa dùng. Mỗi finding khớp đúng 1 signal_id trong evidence_anchors; section có signal thì KHÔNG viết finding ngoài manifest.
- KHÔNG tạo finding về tiết lộ thương mại / #qc / #ad / Luật Quảng cáo disclosure — ngoài phạm vi sản phẩm video diagnosis.
- Section không issue-based (next_video, niche_pattern, channel_pattern, douyin_origin, boost_attribution): findings: [].
- persona: khi emit riêng hoặc cùng script_structure — section.text 2-3 câu (≤55 từ) về giọng/chân thực; tối đa 2 findings; UI gộp vào trục «Giọng & persona» trong «Phân tích cấu trúc Video».
- Tín hiệu seeding/ads/boost (signal section_id=boost_attribution) chỉ được diễn đạt MỘT lần — trong text của section boost_attribution. KHÔNG lặp lại thành finding hay nhắc lại trong section khác.
- Số liệu inline dạng (234K views), (62% mẫu 380) — giải thích ý nghĩa trong cùng câu.
- Khi USER_EVIDENCE_DIGEST có hook_timeline / scene_pattern: body_vi của finding về hook/editing phải trích đúng mốc giây từ digest («text overlay chỉ xuất hiện 3.2s») — bằng chứng đến từng giây, không phỏng đoán.
- evidence_ref (BẰNG CHỨNG TRONG CHÍNH CLIP): với mỗi finding ĐIỂM MẠNH (fix_vi «Tiếp tục»/«Giữ») và mỗi finding về hook/nhịp/cảnh, gắn evidence_ref {start_sec, end_sec, label_vi} = khoảng giây TRONG CLIP ĐANG PHÂN TÍCH chứng minh nhận định — lấy từ hook_timeline/scene_pattern trong USER_EVIDENCE_DIGEST. start_sec/end_sec phải nằm trong độ dài video; end_sec > start_sec; label_vi ≤6 từ tiếng Việt. KHÔNG bịa mốc giây khi digest không có timestamp tương ứng → bỏ evidence_ref (null). evidence_ref CHỈ trỏ vào clip đang phân tích, KHÔNG phải video peer.
- CHỐNG pad: mỗi câu advance argument; không lặp ý. evidence_anchors khớp claim trong text.

DIAGNOSIS (2 yêu cầu thêm — Lightreel contract):
- Câu verdict đặt **tên archetype 2-4 từ tự đặt** cho cách video này làm nội dung («Ảnh catalog tĩnh», «Quy trình đóng hộp», «Mặt người kể chuyện») — findings và next_video gọi lại đúng tên đó để hành động bám chẩn đoán.
- Nêu 1 điểm GIỮ NGUYÊN có bằng chứng (kể cả khi video yếu — vd nhịp cắt, giọng đọc, texture cận) — fix không được phá cái đang chạy.

REFERENCE TILES (làm bằng chứng nổi bật — không chôn trong prose):
- Section show được trực quan (niche_pattern, diagnosis, hook_analysis, script_structure): điền tối đa **3** embedded_tiles **khác aweme_id** từ REFERENCE_EVIDENCE. niche_pattern ưu tiên đủ 3 tile — đây là lưới "top ngách đang làm gì", reference là nhân vật chính, prose dẫn vào chỉ 1 câu.
- Mỗi aweme_id chỉ dùng ở MỘT section. narrative_vi = 1 câu (tối đa 2) **khác nhau cho từng video**: nêu **điều cần học theo** (hook/format/nhịp cụ thể) so với clip đang phân tích — chỉ gắn vào **khoảng trống/thiếu sót**, KHÔNG gắn vào điểm mạnh («Tiếp tục»/«Giữ»). Điểm mạnh chứng minh bằng mốc giây/cảnh của clip đang phân tích (digest), không bằng video peer. Góc theo section (hook_analysis → 3 giây đầu; diagnosis/niche_pattern → format/hiệu quả). KHÔNG nhắc @handle hay số view (card đã hiển thị). KHÔNG lặp narrative_vi vào text. Tuân thủ ADDRESSING_MODE trong DIAGNOSTIC_CONTEXT.
- Chỉ chọn video gần context (CTX_SUMMARY). Không đủ peer phù hợp → ít tile hơn hoặc [].
- Section phân tích thuần (channel_pattern, compliance): tile tùy chọn, không bắt buộc. persona khi emit: prose + findings bắt buộc (trục «Giọng & persona»); peer refs thường nằm ở script_structure/sound.

CHANNEL_PATTERN (Ref-style: kênh tự chứng minh):
- Dùng channel_context: trích số cụ thể (top video X views, bottom Y views, mức view thường của kênh). 1 câu verdict in đậm: video này so với mức thường của kênh thế nào + creator nên nhân đôi cái gì. ≤90 từ. Nếu source="live": ghi chú nhẹ dữ liệu kênh là live.
- Nếu channel_context.recent_content_audit có mặt: được trích số đếm thật để nối video này với pattern kênh («video này không có mặt người — X/Y video gần nhất của kênh cũng vậy»; avg_views_with_face vs without nếu có). KHÔNG suy đoán ngoài số đếm.

NEXT_VIDEO (script copy-paste được, KHÔNG concept trừu tượng):
- next_video là object { "hook_vi", "premise_vi", "format", "reason_vi", "expected_views_range" }; findings: [].
- text của section = script theo cảnh, mỗi dòng 1 bullet •: "• Hook (0-1s): [câu copy-paste]" → "• Beat 2: ..." → "• Beat 3: ..." → "• CTA: ...". Creator phải quay được ngay mà không cần nghĩ thêm.
- Bullets PHẢI theo thứ tự thời gian: Hook → Beat 1 → Beat 2 → CTA cuối cùng — mốc giây tăng dần, KHÔNG đảo Beat/CTA lên trước Hook.
- KHÔNG dán video_id/aweme_id thô (chuỗi 15-19 chữ số) vào prose hay reason_vi — nhắc video tham chiếu bằng format + view («video talking_head 1.2M view», kèm @handle nếu có).
- GIỮ / ĐỔI (chống lặp + chống đập đi xây lại): reason_vi nêu 1 điều GIỮ từ video đang phân tích (có bằng chứng chạy được) và 1 điều ĐỔI then chốt — nối đúng tên archetype đã đặt ở diagnosis.
- Beat script bám NHỊP của đúng 1 video trong REFERENCE_EVIDENCE (reason_vi nói rõ học nhịp video nào, vì sao) — học cấu trúc đã thắng, không sáng tác từ con số 0.

NICHE_PATTERN:
- embedded_tiles từ reference pool (ưu tiên đủ 3); findings: []. Nếu có cross_format_signal: 1 câu verdict in đậm — "format X đang chạy ở N ngách / hook nào đạt view cao nhất" + creator học gì. Phải ra conclusion, không chỉ mô tả.
- KHÓA PATTERN: khi đủ ≥3 tile và có USER_EVIDENCE_DIGEST, câu verdict in đậm = mẫu số chung của CHÍNH các tile đã chọn + video này làm gì khác («Cả 3 video tham chiếu mở bằng mặt người nói trong 1s đầu — video này vào thẳng sản phẩm đến 3.2s»). Không bịa mẫu số chung ngoài tile đã trích; thiếu tile hoặc thiếu digest → verdict thường.
- Ngôn ngữ: tiếng Việt peer-to-peer. Dùng **view** (không "lượt xem"), **tỷ lệ tương tác** (không "engagement rate"). Tránh quote tiếng Anh thô — diễn đạt format/hook bằng tiếng Việt. Khi performance_tier=hit: khung breakout, hook chỉ là polish — không mô tả như flop.
- ENUM PHẢI DỊCH: mọi enum kỹ thuật trong SIGNAL_MANIFEST / USER_ANALYSIS (hook_type, conversion_objective, content_format, first_frame_type…) phải diễn đạt bằng nhãn tiếng Việt — KHÔNG thả enum thô («curiosity_gap», «entertainment_first», «product_closeup») vào câu. SIGNAL_MANIFEST đã kèm nhãn tiếng Việt — dùng đúng nhãn đó.

KHÁCH QUAN VỚI PERFORMANCE_TIER (chống bias kết quả):
- performance_tier là KẾT QUẢ cần giải thích, KHÔNG phải kết luận cần biện minh. Đối chiếu evidence trước khi quy lỗi nội dung: nếu USER_EVIDENCE_DIGEST / retention / tỷ lệ tương tác mạnh mà view thấp → nói thẳng vấn đề nằm ở hook/phân phối, KHÔNG bịa lỗi cấu trúc cho đủ bài.
- tier=hit: vẫn nêu ít nhất 1 điểm cải thiện cụ thể — không tâng bốc toàn bài.
- user_stats.views_vs_avg_ratio gần ranh giới (0.4-0.6 hoặc 1.6-2.4): tránh giọng thắng/thua tuyệt đối — mô tả là "quanh chuẩn format".
- tier=early (video <3 ngày, view chưa ổn định): chẩn đoán cấu trúc bình thường nhưng KHÔNG kết luận video flop; nói rõ số liệu còn sớm, sẽ rõ sau vài ngày.
"""

DIAGNOSIS_V6_SHORTEN_RETRY_APPEND = """
BẮT BUỘC RÚT GỌN: Bản trước quá dài. Trả lại JSON đầy đủ cùng schema.
- TỔNG ≤520 từ (mọi section.text + findings) — ưu tiên giữ đủ 3 trục cấu trúc (script_structure + sound + persona khi có trong SECTIONS_TO_EMIT).
- Mỗi section.text (trừ next_video): ≤90 từ; script_structure ≤100; sound/persona ≤55 — 1 verdict **in đậm** + tối đa 4 câu.
- Giữ đủ findings và embedded_tiles (≥1 tile / thiếu sót rhythm); cắt prose thừa, KHÔNG bỏ fix_vi.
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
    # P3 follow-up — compact per-feature counts (face/hook/overlay/audio role)
    # over the creator's recent analysed corpus rows. Already count-shaped,
    # so it passes through whole.
    audit = cc.get("recent_content_audit")
    if isinstance(audit, dict) and audit:
        out["recent_content_audit"] = audit
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
            # Translate the raw event enum (face_enter, text_overlay…) to its
            # Vietnamese label here — the synthesis is told to cite this digest
            # verbatim, so a raw code leaks straight into the report prose.
            label_raw = str(ev.get("event") or ev.get("type") or "?")
            label = hook_timeline_event_vi(label_raw, default=_humanize_code(label_raw))
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
            # overlay_style has a Vietnamese map; framing/pace are humanized
            # (underscores → spaces) so no raw enum code reaches the prose.
            dim_parts: list[str] = []
            for k in ("framing", "pace", "overlay_style"):
                v = sc.get(k)
                if not v:
                    continue
                dim_parts.append(
                    overlay_style_vi(str(v), default=_humanize_code(str(v)))
                    if k == "overlay_style"
                    else _humanize_code(str(v))
                )
            dims = "/".join(dim_parts)
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
            for k in (
                "caption", "views", "hashtags", "music_origin", "duration_sec",
                # Anti-bias context: the LLM sees the ratio that generates the
                # tier (and the video's age) — not just the label.
                "views_vs_avg_ratio", "video_age_days",
                "stats_history", "distribution_shape",
            )
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
            "\n- SECTION diagnosis («Đang làm tốt»): điểm mạnh (fix_vi «Tiếp tục»/«Giữ»/«Duy trì») "
            "chứng minh bằng mốc giây/cảnh trong USER_EVIDENCE_DIGEST của CHÍNH clip đang phân tích — "
            "KHÔNG gắn embedded_tiles peer cho điểm mạnh. Peer reference chỉ khi có khoảng trống "
            "(fix_vi sửa cụ thể) — narrative_vi nêu peer xử lý gap đó tốt hơn."
            "\n- Nếu chỉ có điểm mạnh, không có khoảng trống: embedded_tiles của diagnosis = []."
        )
    strength_gap_note = ""
    if tier == "average" and "diagnosis" in sections_to_emit:
        strength_gap_note = (
            "\n\nSECTION diagnosis (tier=average — «Điểm mạnh và khoảng trống»):"
            "\n- section.text: ưu tiên 4 câu trong ngân sách ≤90 từ (1 verdict **in đậm** + 3 câu "
            "chứng minh có số liệu/mốc giây). Đây là đoạn dẫn nhập — đọc xong phải hiểu vì sao "
            "video quanh chuẩn ngách."
            "\n- findings: đúng 1 điểm mạnh (fix_vi bắt đầu «Tiếp tục»/«Giữ»/«Duy trì») + 1-2 "
            "khoảng trống (fix_vi là hành động sửa cụ thể). UI tách hai nhóm — đừng gộp lẫn."
            "\n- embedded_tiles narrative_vi: 1-2 câu mô tả peer làm gì tốt hơn clip đang phân tích "
            "VÀ gắn trực tiếp vào 1 khoảng trống («để sửa hook chung chung, clip này mở bằng…»). "
            "KHÔNG dùng câu chung «Được chọn vì format» / «Tham chiếu vì» không nói áp dụng cho gap nào."
            "\n- Dệt 1-2 câu trong section.text dẫn sang thẻ video tham chiếu (thumbnail); "
            "không lặp nguyên văn narrative_vi trên thẻ."
        )
    hook_analysis_note = ""
    if "hook_analysis" in sections_to_emit:
        hook_analysis_note = (
            "\n\nSECTION hook_analysis («Phân tích hook»):"
            "\n- section.text: ưu tiên ≤90 từ (1 verdict **in đậm** + tối đa 4 câu "
            "về 3 giây đầu: loại hook, text overlay, lời thoại, visual layering, mute-safe). "
            "Mật độ prose tương đương block «Đang làm tốt» — đọc xong hiểu hook mạnh/yếu thế nào."
            "\n- findings: đúng 1 điểm mạnh (fix_vi «Tiếp tục»/«Giữ»/«Duy trì») + "
            "1-2 thiếu sót hook (fix_vi hành động copy-paste, có mốc giây). UI tách ĐIỂM MẠNH / THIẾU SÓT."
            "\n- Mỗi thiếu sót BẮT BUỘC có fix_vi riêng — KHÔNG ghi critique hook chỉ trong section.text."
            "\n- embedded_tiles: đúng 1 tile cho mỗi thiếu sót (tối đa 3) — narrative_vi "
            "nêu peer xử lý 3 giây đầu tốt hơn («để sửa overlay trễ, clip này hiện text 0,4s…»). "
            "KHÔNG «Được chọn vì format» chung chung."
            "\n- Dệt 1-2 câu cuối section.text dẫn sang thẻ tham chiếu (hook cụ thể); "
            "không lặp nguyên văn narrative_vi trên thẻ."
        )
    video_structure_note = ""
    has_script_structure = "script_structure" in sections_to_emit
    has_editing = "editing" in sections_to_emit
    has_sound = "sound" in sections_to_emit
    has_persona = "persona" in sections_to_emit
    if has_script_structure:
        merge_bits = []
        if has_editing:
            merge_bits.append("editing")
        if has_sound:
            merge_bits.append("sound")
        if has_persona:
            merge_bits.append("persona")
        merge_hint = (
            f" (UI gộp {' + '.join(merge_bits)} vào «Phân tích cấu trúc Video» sau hook)"
            if merge_bits
            else ""
        )
        axis_n = 1 + sum(1 for x in (has_editing, has_sound, has_persona) if x)
        video_structure_note = (
            f"\n\nBLOCK «Phân tích cấu trúc Video»{merge_hint} — {axis_n} TRỤC RIÊNG trên UI "
            "(mỗi trục = section BE riêng; FE gộp sau hook):"
            "\n\nTRỤC 1 — script_structure («Nhịp & cắt»):"
            "\n- section.text: 2-3 câu (≤100 từ): 1 verdict **in đậm** + câu về nhịp cắt, "
            "pattern interrupt, dead air, góc quay/framing, chuyển cảnh — KHÔNG lẫn hook 3s đầu."
            "\n- findings: đúng 1 điểm mạnh (fix_vi «Tiếp tục»/«Giữ»/«Duy trì») + "
            "1-2 thiếu sót nhịp/cảnh/cách quay (fix_vi copy-paste, có mốc giây/scene)."
            "\n- embedded_tiles: 1 tile / thiếu sót (tối đa 3) — narrative_vi nêu peer xử lý "
            "nhịp/cảnh tốt hơn. KHÔNG «Được chọn vì format»."
        )
        truc = 2
        if has_editing:
            video_structure_note += (
                f"\n\nTRỤC {truc} — editing («Hậu kỳ & hình»):"
                "\n- section.text: **BẮT BUỘC** 2-3 câu (≤55 từ) về color grade, chữ overlay, "
                "framing/hậu kỳ, LUT/filter — KHÔNG lẫn nhịp cắt hay hook."
                "\n- findings: 1 điểm mạnh HOẶC 1 thiếu sót hậu kỳ/chữ trên hình (fix_vi cụ thể)."
                "\n- embedded_tiles: 0-1 tile gắn thiếu sót editing nếu có peer phù hợp."
            )
            truc += 1
        if has_sound:
            video_structure_note += (
                f"\n\nTRỤC {truc} — sound («Âm thanh»):"
                "\n- section.text: **BẮT BUỘC** 2-3 câu (≤55 từ) về nhạc nền, voiceover, "
                "sound layering, trending vs original — KHÔNG để trống."
                "\n- findings: 1 điểm mạnh HOẶC 1 thiếu sót âm thanh (fix_vi cụ thể)."
                "\n- embedded_tiles: 0-1 tile gắn thiếu sót âm nếu có peer phù hợp."
            )
            truc += 1
        if has_persona:
            video_structure_note += (
                f"\n\nTRỤC {truc} — persona («Giọng & persona»):"
                "\n- section.text: **BẮT BUỘC** 2-3 câu (≤55 từ) về giọng, persona on-camera, "
                "register, chân thực — KHÔNG để trống."
                "\n- findings: 1 điểm mạnh HOẶC 1 thiếu sót persona (fix_vi copy-paste)."
                "\n- embedded_tiles: [] (peer refs thuộc script_structure/sound/editing khi có)."
            )
        if not has_editing and not has_sound and not has_persona:
            video_structure_note += (
                "\n- Chỉ trục Nhịp & cắt khi editing/sound/persona không có trong SECTIONS_TO_EMIT."
            )
    elif has_editing:
        video_structure_note = (
            "\n\nBLOCK «Phân tích cấu trúc Video» (chỉ editing trong SECTIONS_TO_EMIT):"
            "\n- section.text: 2-3 câu (≤55 từ) về color grade, chữ overlay, hậu kỳ — KHÔNG để trống."
            "\n- findings: ≥1 về hậu kỳ/chữ trên hình (fix_vi cụ thể, copy-paste)."
            "\n- embedded_tiles: 0-1 tile gắn thiếu sót editing nếu có peer phù hợp."
        )
    elif has_sound:
        video_structure_note = (
            "\n\nBLOCK «Phân tích cấu trúc Video» (chỉ sound trong SECTIONS_TO_EMIT):"
            "\n- section.text: 2-3 câu (≤55 từ) về âm thanh — KHÔNG để trống."
            "\n- findings: ≥1 về âm thanh (fix_vi cụ thể, copy-paste)."
            "\n- embedded_tiles: 0-1 tile gắn thiếu sót âm nếu có peer phù hợp."
        )
    elif has_persona:
        video_structure_note = (
            "\n\nBLOCK «Phân tích cấu trúc Video» (chỉ persona trong SECTIONS_TO_EMIT):"
            "\n- section.text: 2-3 câu (≤55 từ) về giọng/persona — KHÔNG để trống."
            "\n- findings: ≥1 về giọng/chân thực on-camera (fix_vi copy-paste)."
            "\n- embedded_tiles: [] (peer refs khi có script_structure)."
        )
    blocks.append(
        "\n\nViết JSON đầy đủ theo schema. Mỗi section.text: 1 câu verdict in đậm + tối đa 4 câu "
        "chứng minh (≤90 từ; script_structure ≤100 từ). Tổng báo cáo ~350-450 từ. Ưu tiên fix + "
        "reference video hơn giải thích dài. KHÔNG tạo section timing/giờ đăng. Mỗi câu phải "
        "advance argument."
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
        "\n- Nhịp đúng (≤90 từ; script_structure ≤100): '**Hình mẫu X đang kéo view tốt** so với "
        "chuẩn ngách. ASMR + trắc nghiệm tạo tò mò. Vượt 1,8× mức view thường kênh. "
        "Hai clip tham chiếu dưới minh họa cách xử lý hook và nhịp.'"
        + tier_note
        + strength_gap_note
        + hook_analysis_note
        + video_structure_note
    )
    return "".join(blocks)
