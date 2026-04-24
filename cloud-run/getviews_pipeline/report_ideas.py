"""Phase C.3 — Ideas report aggregator (fixture + live pipeline + variant mode)."""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.report_types import (
    ActionCardPayload,
    ConfidenceStrip,
    IdeaBlockPayload,
    IdeasPayload,
    SourceRow,
    validate_and_store_report,
)

logger = logging.getLogger(__name__)


# ── Fixture path (C.1.2) ─────────────────────────────────────────────────────


def _fixture_idea(rank: int, title: str, hook: str, tag: str = "listicle") -> IdeaBlockPayload:
    return IdeaBlockPayload(
        id=str(rank),
        title=title,
        tag=tag,
        angle=f"Góc {rank}: đánh trúng pain mở đầu + twist trong 2s.",
        why_works="Cụm hook này đạt median retention cao hơn baseline ngách.",
        evidence_video_ids=[],
        hook=hook,
        slides=[
            {"step": i, "body": f"Slide {i} — cảnh hành động cụ thể"} for i in range(1, 7)
        ],
        metric={"label": "RETENTION DỰ KIẾN", "value": "72%", "range": "64–80%"},
        prerequisites=["Face visible 0–1s", "On-screen text mở đầu"],
        confidence={"sample_size": 12, "creators": 5},
        style="handheld",
    )


def _standard_fixture_ideas() -> list[IdeaBlockPayload]:
    seeds = [
        ("01", "Mình vừa test ___ và", "Mình vừa test ChatGPT Pro và…", "testimonial"),
        ("02", "Không ai nói với bạn là ___", "Không ai nói là iPhone 15 có…", "curiosity_gap"),
        ("03", "POV: bạn vừa phát hiện ___", "POV: bạn vừa phát hiện 3 feature", "pov"),
        ("04", "5 thứ ___ không nói với bạn", "5 điều sếp IT không nói với bạn", "listicle"),
        ("05", "Bạn đang xem ___ sai cách", "Bạn đang dùng ChatGPT sai cách", "bold_claim"),
    ]
    out: list[IdeaBlockPayload] = []
    for i, (rank, title, hook, tag) in enumerate(seeds, start=1):
        out.append(_fixture_idea(i, title, hook, tag=tag))
        out[-1].id = rank
    return out


def build_fixture_ideas_report() -> dict[str, Any]:
    """C.1 fixture — validates as IdeasPayload (standard variant, full sample)."""
    confidence = ConfidenceStrip(
        sample_size=72,
        window_days=7,
        niche_scope="Tech",
        freshness_hours=3,
        intent_confidence="high",
    )
    payload = IdeasPayload(
        confidence=confidence,
        lead=(
            "Dựa trên 72 video thắng trong ngách Tech tuần này, đây là 5 kịch bản "
            "giữ retention ≥ 64%. Mỗi kịch bản kèm slide-by-slide và góc quay đề xuất."
        ),
        ideas=_standard_fixture_ideas(),
        style_cards=[
            {"id": "1", "name": "Handheld P2P", "desc": "Cầm tay, mắt nhìn camera, cắt nhanh.", "paired_ideas": ["#1", "#3"]},
            {"id": "2", "name": "Screen record overlay", "desc": "Màn hình + text bản địa hóa.", "paired_ideas": ["#2"]},
            {"id": "3", "name": "Before / after", "desc": "So sánh 2 trạng thái, 3–5s mỗi bên.", "paired_ideas": ["#4"]},
            {"id": "4", "name": "Desk demo", "desc": "Bàn làm việc gọn, ánh sáng 45°.", "paired_ideas": ["#5"]},
            {"id": "5", "name": "Voice-led", "desc": "Dựa vào voiceover, cut B-roll.", "paired_ideas": ["#1", "#4"]},
        ],
        stop_doing=[
            {"bad": "Hook 4s dài dòng", "why": "Drop-off tăng 34% sau giây 3.", "fix": "Cắt hook ≤ 1.4s, nêu số liệu/claim."},
            {"bad": "CTA 'Follow to see more'", "why": "CTR comment thấp 2.1×.", "fix": "Hỏi ngược: 'Bạn thấy sao?'."},
            {"bad": "Nhạc trending ngoài niche", "why": "Retention giảm khi audio lệch tone.", "fix": "Sound gốc hoặc trending cùng ngách."},
            {"bad": "Text overlay mờ", "why": "Mobile ≤ 30% nhìn rõ text nhỏ.", "fix": "Font ≥ 42pt, viền trắng 2px."},
            {"bad": "Video > 60s mà không có payoff", "why": "Retention drop 41% sau 60s.", "fix": "Payoff ≤ 45s hoặc chuyển carousel."},
        ],
        actions=[
            ActionCardPayload(
                icon="sparkles",
                title="Mở Xưởng Viết với ý #1",
                sub="Dùng hook 'Mình vừa test ___ và'",
                cta="Mở",
                primary=True,
                route="/app/script",
                forecast={"expected_range": "8K–15K", "baseline": "6.2K"},
            ),
            ActionCardPayload(
                icon="save",
                title="Lưu cả 5 ý tưởng",
                sub="Đưa vào lịch quay 7 ngày",
                cta="Lưu",
                route="/app/history",
                forecast={"expected_range": "—", "baseline": "—"},
            ),
        ],
        sources=[SourceRow(kind="video", label="Corpus", count=72, sub="Tech · 7d")],
        related_questions=[
            "Hook nào đang giảm trong ngách?",
            "Slide-by-slide cho ý tưởng #1?",
            "5 cách viết hook cho listicle?",
        ],
        variant="standard",
    )
    return payload.model_dump()


ANSWER_FIXTURE_IDEAS: dict[str, Any] = validate_and_store_report(
    "ideas",
    build_fixture_ideas_report(),
)


def build_thin_corpus_ideas_report() -> dict[str, Any]:
    """Empty-state shape: sample_size < 60 → 3 ideas, skip stop_doing (plan §2.2)."""
    inner = build_fixture_ideas_report()
    conf = inner["confidence"]
    if isinstance(conf, dict):
        conf["sample_size"] = 42
    inner["lead"] = (
        "Mẫu nhỏ: 42 video trong ngách này 7 ngày qua — 3 hướng bên dưới chỉ dùng "
        "để định hướng, không kết luận toàn ngách."
    )
    inner["ideas"] = inner["ideas"][:3]
    inner["stop_doing"] = []
    return inner


def build_hook_variants_report(seed_hook: str | None = None) -> dict[str, Any]:
    """Variant mode (intent 16): 5 hook phrasings of a seed, no stop_doing."""
    seed = seed_hook or "Mình vừa test ___ và"
    inner = build_fixture_ideas_report()
    inner["lead"] = f"5 cách viết hook \u201c{seed}\u201d — cùng góc, khác câu mở."
    inner["variant"] = "hook_variants"
    inner["stop_doing"] = []
    variants = [
        f"{seed}",
        f"{seed.rstrip()} đây là điều mình không ngờ",
        f"{seed.rstrip()} kết quả làm mình đổi hẳn cách dùng",
        f"{seed.rstrip()} và 3 thứ không ai nói với bạn",
        f"{seed.rstrip()} 7 ngày sau thì…",
    ]
    # Variant mode: 2–3 bullets instead of 6-slide accordion.
    for i, idea in enumerate(inner["ideas"]):
        idea["title"] = f"Biến thể {i + 1}"
        idea["tag"] = "hook_variant"
        idea["hook"] = variants[i]
        idea["slides"] = [
            {"step": 1, "body": "Quay mặt nhìn camera, đọc hook đến khi kết thúc claim."},
            {"step": 2, "body": "Payoff: 1 ví dụ cụ thể, show màn hình / sản phẩm."},
            {"step": 3, "body": "CTA: hỏi ngược 1 câu, không dùng 'follow'."},
        ]
        idea["angle"] = "Giữ nguyên góc nội dung; chỉ đổi cách mở câu."
        idea["why_works"] = "Cùng cấu trúc retention, đổi câu mở để test A/B."
    return inner


# ── Live pipeline (C.3.2) ────────────────────────────────────────────────────


def build_ideas_report(
    niche_id: int,
    query: str,
    intent_type: str,
    window_days: int = 7,
    variant: str = "standard",
) -> dict[str, Any]:
    """Live Ideas report. Falls back to fixture when DB / niche is unavailable.

    Variant selection:
    - ``variant == "hook_variants"`` → hook-phrasing mode, suppresses stop_doing.
    - Any other value → standard.

    Empty state (sample_size < 60 in standard mode) → thin-corpus fixture.
    """
    v = "hook_variants" if variant == "hook_variants" else "standard"
    if v == "hook_variants":
        inner = build_hook_variants_report(seed_hook=query if query else None)
        if isinstance(inner.get("confidence"), dict):
            inner["confidence"]["window_days"] = window_days
        return inner

    try:
        from getviews_pipeline.supabase_client import get_service_client

        sb = get_service_client()
    except Exception as exc:
        logger.warning("[ideas] service client unavailable: %s — fixture path", exc)
        data = build_fixture_ideas_report()
        if isinstance(data.get("confidence"), dict):
            data["confidence"]["window_days"] = window_days
        return data

    from getviews_pipeline.report_ideas_compute import (
        compute_ideas_blocks,
        compute_stop_doing,
        compute_style_cards,
        load_ideas_inputs,
        rank_hooks_for_ideas,
        static_ideas_action_cards,
    )

    ctx = load_ideas_inputs(sb, niche_id, window_days)
    if ctx is None:
        data = build_fixture_ideas_report()
        if isinstance(data.get("confidence"), dict):
            data["confidence"]["window_days"] = window_days
        return data

    ni = ctx["ni"]
    he_rows: list[dict[str, Any]] = ctx["he_rows"]
    corpus: list[dict[str, Any]] = ctx["corpus"]
    niche_label = str(ctx["niche_label"])
    style_distribution: list[dict[str, Any]] = ctx.get("style_distribution") or []

    sample_n = int(ni.get("sample_size") or 0)
    ranked = rank_hooks_for_ideas(he_rows)
    if niche_id <= 0 or sample_n < 60 or len(ranked) < 3:
        thin = build_thin_corpus_ideas_report()
        if isinstance(thin.get("confidence"), dict):
            thin["confidence"]["window_days"] = window_days
            thin["confidence"]["niche_scope"] = niche_label
        return thin

    org = float(ni.get("organic_avg_views") or 0)
    com = float(ni.get("commerce_avg_views") or 0)
    baseline_views = org if org > 0 else (com if com > 0 else 1.0)

    ideas_blocks = compute_ideas_blocks(ranked, corpus, baseline_views)
    style_cards = compute_style_cards(style_distribution, n=5, fallback_niche=niche_label)
    stop_rows = compute_stop_doing(he_rows, baseline_views)
    action_cards = static_ideas_action_cards(baseline_views, top_idea_hook=ideas_blocks[0].hook if ideas_blocks else None)

    confidence = ConfidenceStrip(
        sample_size=sample_n,
        window_days=window_days,
        niche_scope=niche_label,
        freshness_hours=_freshness_from_corpus(corpus),
        intent_confidence="high" if sample_n >= 120 else "medium",
    )

    # 2026-04-22 fix — ``lead`` + ``related_questions`` were hardcoded,
    # so every ideas follow-up in the same niche read the same sentence.
    # Route through the new Gemini-backed narrative so the copy reflects
    # the specific question (falls back deterministically on no-key /
    # budget exhausted envs — the fallback is still query-aware).
    from getviews_pipeline.report_ideas_gemini import fill_ideas_narrative

    top_idea_hooks = [b.hook for b in ideas_blocks[:5] if getattr(b, "hook", None)]
    narrative = fill_ideas_narrative(
        query=query,
        niche_label=niche_label,
        sample_n=sample_n,
        top_idea_hooks=top_idea_hooks,
    )

    # 2026-05-10 — Wave 2 PR #3: merge Gemini per-rank copy into each
    # IdeaBlockPayload. Overrides the deterministic opening_line from
    # compute_ideas_blocks (Wave 2 PR #2) and fills content_angle via
    # the existing `angle` field. If Gemini returned an empty
    # hook_lines list (fallback path / network error), deterministic
    # templates stay in place — no loss of output.
    hook_lines = narrative.get("hook_lines") or []
    if hook_lines:
        by_rank = {int(hl["rank"]): hl for hl in hook_lines}
        updated_blocks: list[IdeaBlockPayload] = []
        for block in ideas_blocks:
            hl = by_rank.get(block.rank)
            if hl:
                block = block.model_copy(update={
                    "opening_line": hl.get("opening_line") or block.opening_line,
                    "angle": hl.get("content_angle") or block.angle,
                })
            updated_blocks.append(block)
        ideas_blocks = updated_blocks

    # 2026-05-10 — Wave 2 PR #1: inject Layer 0 niche_insights data.
    # See report_pattern.py for the same pattern. Null-safe if the
    # Layer 0 cron hasn't run for this niche yet.
    from getviews_pipeline.niche_insight_fetcher import fetch_niche_insight
    niche_insight = fetch_niche_insight(niche_id, client=sb)

    payload = IdeasPayload(
        confidence=confidence,
        lead=narrative["lead"],
        ideas=ideas_blocks,
        style_cards=[c.model_dump() if hasattr(c, "model_dump") else c for c in style_cards],
        stop_doing=stop_rows,
        actions=action_cards,
        sources=[SourceRow(kind="video", label="Corpus", count=sample_n, sub=f"{niche_label} · {window_days}d")],
        related_questions=narrative["related_questions"],
        variant="standard",
        niche_insight=niche_insight,
    )
    return payload.model_dump()


def _freshness_from_corpus(corpus: list[dict[str, Any]]) -> int:
    from datetime import datetime, timezone

    best: datetime | None = None
    for row in corpus:
        raw = row.get("indexed_at") or row.get("created_at")
        if not raw:
            continue
        try:
            d = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if best is None or d > best:
            best = d
    if best is None:
        return 24
    delta = datetime.now(timezone.utc) - best.astimezone(timezone.utc)
    return max(1, int(delta.total_seconds() // 3600))
