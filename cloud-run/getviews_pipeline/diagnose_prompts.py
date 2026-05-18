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
    "headline_vi": "một câu ≤20 từ — finding mạnh nhất",
    "sections": [
      {
        "section_id": "<id>",
        "title": "tiêu đề tiếng Việt",
        "text": "2-3 đoạn văn, mỗi đoạn cách nhau bằng \\n\\n, tối thiểu ~200 từ mỗi section khi có đủ evidence",
        "embedded_tiles": [],
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
- Chỉ tạo các section có trong SECTIONS_TO_EMIT, đúng thứ tự đó.
- Mỗi section: prose tiếng Việt. Bullet points (dấu •) CHỈ dùng khi liệt kê bước hành động cụ thể, checklist, hoặc danh sách song song — ưu tiên cho: next_video (việc creator cần làm), script_structure (checklist cấu trúc cần sửa), niche_pattern (pattern list), hook_analysis (các lỗi hook cụ thể). Các section phân tích sâu (diagnosis, channel_pattern, sound, persona, compliance, distribution) dùng prose thuần — bullet trong những mục này là dấu hiệu của suy nghĩ hời hợt.
- Bullet format: "• [hành động cụ thể]" — mỗi bullet ≤2 dòng, ngắt bằng ký tự xuống dòng đơn (\n), đoạn prose cách bullet bằng dòng trắng (\n\n).
- Số liệu inline dạng (234K views), (62% mẫu 380) — giải thích ý nghĩa trong cùng đoạn.
- CHỐNG pad: mỗi câu phải advance argument; không lặp lại cùng một ý.
- evidence_anchors khớp với các claim trong text.
- next_video section: next_video là object { "hook_vi", "premise_vi", "format", "reason_vi", "expected_views_range" } CHỈ cho section đó; text của section này có thể liệt kê 3-5 bullet • những việc creator cần làm cụ thể để thực hiện concept.
- niche_pattern: có thể điền embedded_tiles với aweme_id từ reference pool (thumbnail_url optional).
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
    collapsed_questions: list[str] | None = None,
) -> str:
    tier = str(performance_tier or "unknown").lower()
    default_titles = {
        sid: default_section_title(sid, tier) for sid in sections_to_emit
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
        "channel_context_available": bool(channel_context and channel_context.get("available")),
        "errors_head": (errors or [])[:3],
    }
    blocks = [
        DIAGNOSIS_V6_JSON_INSTRUCTION.strip(),
        "\nDIAGNOSTIC_CONTEXT_JSON:\n",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "\n\nUSER_ANALYSIS_JSON (truncated keys):\n",
        json.dumps(
            {k: user_analysis.get(k) for k in list(user_analysis.keys())[:24]},
            ensure_ascii=False,
        ),
    ]
    if corpus_citation:
        blocks.append(f"\n\nCORPUS_CITATION_BLOCK:\n{corpus_citation}")
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
    blocks.append(
        "\n\nViết JSON đầy đủ theo schema. Các section.text phải đạt chiều sâu ~200+ "
        "từ/section khi context đủ (mục tiêu tổng 1500–2000 từ cho báo cáo đầy đủ)."
    )
    return "".join(blocks)
