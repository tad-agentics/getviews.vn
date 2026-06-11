"""Phase C.2 — Pattern report aggregator (fixture + live pipeline hook)."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import UTC
from typing import Any

from getviews_pipeline.report_pattern_compute import (
    build_micro_context,
    build_pattern_cells,
    build_tldr_callouts,
    build_top_performers_context,
    compute_findings,
    compute_what_stalled,
    fetch_outlier_story,
    find_ab_pair,
    load_pattern_inputs,
    pick_evidence_videos,
    rank_hooks_for_pattern,
    static_action_cards,
)
from getviews_pipeline.report_pattern_gemini import build_why_won_list, fill_pattern_narrative
from getviews_pipeline.report_types import (
    ActionCardPayload,
    ConfidenceStrip,
    ContrastAgainst,
    EvidenceCardPayload,
    HookFinding,
    Lifecycle,
    Metric,
    OutlierStory,
    PatternCellPayload,
    PatternPayload,
    SourceRow,
    SumStat,
    WoWDiff,
    validate_and_store_report,
)

logger = logging.getLogger(__name__)


def _metric(val: str, num: float, definition: str) -> Metric:
    return Metric(value=val, numeric=num, definition=definition)


def fetch_pattern_wow_diff_rows(niche_id: int) -> list[dict[str, Any]]:
    """Load WoW rows from ``pattern_wow_diff_7d`` (C.2.1 RPC).

    Returns an empty list when the RPC returns no rows, the stub is in
    effect, or the service client cannot run (local tests without env).
    """
    try:
        from getviews_pipeline.supabase_client import get_service_client

        client = get_service_client()
        res = client.rpc("pattern_wow_diff_7d", {"p_niche_id": niche_id}).execute()
        raw = res.data
        if raw is None:
            return []
        if isinstance(raw, list):
            return [r for r in raw if isinstance(r, dict)]
        if isinstance(raw, dict):
            return [raw]
        return []
    except Exception as exc:
        logger.warning("[pattern] pattern_wow_diff_7d skipped: %s", exc)
        return []


def wow_rows_to_wow_diff(rows: list[dict[str, Any]]) -> WoWDiff:
    """Map RPC rows (``hook_type``, ranks, ``is_new``, ``is_dropped``) to §J ``WoWDiff``."""
    new_entries: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    rank_changes: list[dict[str, Any]] = []
    for r in rows:
        ht = r.get("hook_type")
        if not ht:
            continue
        if r.get("is_new"):
            new_entries.append(dict(r))
        elif r.get("is_dropped"):
            dropped.append(dict(r))
        else:
            rank_changes.append(dict(r))
    return WoWDiff(new_entries=new_entries, dropped=dropped, rank_changes=rank_changes)


def build_fixture_pattern_report() -> dict[str, Any]:
    """C.1 fixture — validates as PatternPayload; WhatStalled invariant: empty + reason."""
    confidence = ConfidenceStrip(
        sample_size=47,
        window_days=7,
        niche_scope="Tech",
        freshness_hours=3,
        intent_confidence="high",
        what_stalled_reason="stub: corpus slice empty for negative quartile",
    )
    lf = Lifecycle(first_seen="2026-01-01", peak="2026-03-15", momentum="rising")
    hf = HookFinding(
        rank=1,
        pattern="Mình vừa test ___ và",
        retention=_metric("74%", 0.74, "viewers past 15s"),
        delta=_metric("+312%", 3.12, "vs niche avg"),
        uses=214,
        lifecycle=lf,
        contrast_against=ContrastAgainst(pattern="Before/after swipe", why_this_won="Opens with curiosity gap"),
        prerequisites=["Face visible 0–1s", "On-screen text"],
        insight="Strong hook retention vs niche baseline.",
        evidence_video_ids=[],
        creator_count=18,
    )
    ev = EvidenceCardPayload(
        video_id="stub-1",
        creator_handle="@demo",
        title="Stub video",
        views=412000,
        retention=0.78,
        duration_sec=28,
        bg_color="#1F2A3B",
        hook_family="testimonial",
        thumbnail_url=None,
        engagement_rate=0.087,
    )
    payload = PatternPayload(
        confidence=confidence,
        wow_diff=WoWDiff(),
        tldr={
            "thesis": "Hook-first testimonials are winning in Tech this week.",
            "callouts": [
                SumStat(label="Videos scanned", value="47", trend="+12%", tone="up"),
                SumStat(label="Median retention", value="72%", trend="+4%", tone="up"),
                SumStat(label="Creators", value="18", trend="flat", tone="neutral"),
            ],
        },
        findings=[hf, hf.model_copy(update={"rank": 2, "pattern": "POV ___"}), hf.model_copy(update={"rank": 3, "pattern": "Listicle 3 điều"})],
        what_stalled=[],
        evidence_videos=[ev] * 6,
        patterns=[
            PatternCellPayload(
                title="Duration",
                finding="28s",
                detail="Mode band",
                chart_kind="duration",
                chart_data={"bars": [14, 20, 28, 32, 36]},
            ),
            PatternCellPayload(
                title="Hook timing",
                finding="0.4s",
                detail="Median",
                chart_kind="hook_timing",
                chart_data={"marker": 0.42},
            ),
            PatternCellPayload(
                title="Sound",
                finding="60% orig",
                detail="Mix",
                chart_kind="sound_mix",
                chart_data={"primary_pct": 60},
            ),
            PatternCellPayload(
                title="CTA",
                finding="Follow",
                detail="Family",
                chart_kind="cta_bars",
                chart_data={"bars": [20, 35, 50, 30, 42]},
            ),
        ],
        actions=[
            ActionCardPayload(
                icon="sparkles",
                title="Mở Xưởng Viết",
                sub="Draft từ hook #1",
                cta="Mở",
                primary=True,
                route="/app/script",
                forecast={"expected_range": "8K–15K", "baseline": "6.2K"},
            ),
            ActionCardPayload(
                icon="search",
                title="Soi kênh đối thủ",
                sub="Benchmark retention",
                cta="Mở",
                route="/app/channel",
                forecast={"expected_range": "—", "baseline": "—"},
            ),
            ActionCardPayload(
                icon="calendar",
                title="Theo dõi trend",
                sub="Tuần này",
                cta="Xem",
                route="/app/trends",
                forecast={"expected_range": "—", "baseline": "—"},
            ),
        ],
        sources=[
            SourceRow(kind="video", label="Corpus", count=47, sub="Tech · 7d"),
        ],
        related_questions=["Hook nào đang giảm?", "Format nào oversaturated?", "Niche con nào đang nổi?"],
        outlier_story=OutlierStory(
            creator_handle="@viral_demo",
            views=3_400_000,
            breakout_ratio=340.0,
            hook_type="Cảnh báo / twist",
            days_ago=2,
        ),
    )
    return payload.model_dump()


# C.1.2 — full §J `ReportV1` envelope for pytest / smoke scripts (`kind` + `report`).
ANSWER_FIXTURE_PATTERN: dict[str, Any] = validate_and_store_report(
    "pattern",
    build_fixture_pattern_report(),
)


def build_empty_pattern_report(
    *,
    niche_label: str = "—",
    window_days: int = 7,
    sample_size: int = 0,
    reason: str = "Chưa dựng được báo cáo cho ngách này. Quay lại sau.",
) -> dict[str, Any]:
    """Live empty-state payload — used whenever the real pipeline can't
    produce a ranked report (service client unavailable, niche corpus
    below threshold, load inputs returns None).

    Crucial invariant: this MUST NOT embed ``@demo`` / ``Stub video``
    evidence cards. The fixture payload does that for offline validation
    + smoke tests, and for months it was mistakenly wired up as a live
    fallback — the QA audit on 2026-04-22 caught 6 identical
    ``@demo / Stub video`` cards in a production Answer response. The fix
    is to render a real empty state the user can actually act on (try a
    different niche, wait for corpus refresh) instead of shipping a
    ``confident-looking but fictitious`` hook ranking.
    """
    confidence = ConfidenceStrip(
        sample_size=max(0, int(sample_size)),
        window_days=int(window_days),
        niche_scope=niche_label,
        freshness_hours=0,
        intent_confidence="low",
        what_stalled_reason=reason,
    )
    payload = PatternPayload(
        confidence=confidence,
        wow_diff=WoWDiff(),
        tldr={
            "thesis": reason,
            "callouts": [],
        },
        findings=[],
        what_stalled=[],
        evidence_videos=[],
        patterns=[],
        actions=[
            ActionCardPayload(
                icon="calendar",
                title="Theo dõi trend",
                sub="Xem khi kho dữ liệu cập nhật",
                cta="Xem",
                route="/app/trends",
                forecast={"expected_range": "—", "baseline": "—"},
            ),
        ],
        sources=[],
        related_questions=[],
    )
    return payload.model_dump()


def build_thin_corpus_pattern_report(
    *,
    sample_size: int = 12,
    niche_label: str = "—",
    window_days: int = 7,
) -> dict[str, Any]:
    """Thin-corpus shape: N<30, humility reason, no stalled rows (C.2.1 pytest contract).

    Built on top of ``build_empty_pattern_report`` — never inherits the
    fixture's ``@demo`` evidence cards. The live pipeline passes the real
    ``niche_intelligence.sample_size`` + niche label so the UI shows the
    actual corpus count.
    """
    data = build_empty_pattern_report(
        niche_label=niche_label,
        window_days=window_days,
        sample_size=sample_size,
        reason="Chưa đủ hook để xếp hạng các điểm cần tránh.",
    )
    data["tldr"] = {
        "thesis": "Tín hiệu định hướng — chưa nên kết luận cho toàn ngách.",
        "callouts": [],
    }
    return data


def _freshness_hours_from_corpus(corpus: list[dict[str, Any]]) -> int:
    from datetime import datetime

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
    delta = datetime.now(UTC) - best.astimezone(UTC)
    return max(1, int(delta.total_seconds() // 3600))


def _pattern_thumb_urls(corpus: list[dict[str, Any]], limit: int = 5) -> list[str]:
    thumbs: list[str] = []
    for row in corpus:
        u = row.get("thumbnail_url") or row.get("thumbnail")
        if isinstance(u, str) and u.strip():
            thumbs.append(u.strip())
        if len(thumbs) >= limit:
            break
    return thumbs


def build_pattern_report(
    niche_id: int,
    query: str,
    _intent_type: str,
    window_days: int = 7,
    *,
    subreports: list[str] | None = None,
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    """C.2.2 — live pattern report: DB aggregators + optional Gemini copy + WoW merge.

    C.5.3 — ``subreports`` attaches auxiliary payloads under ``payload.subreports``
    (e.g. ``{"timing": TimingPayload}``). Only ``"timing"`` is supported today;
    unknown keys are ignored with a ``[pattern]`` warning.
    """
    eff_win = max(int(window_days), 14)
    wow = wow_rows_to_wow_diff(fetch_pattern_wow_diff_rows(niche_id)).model_dump()

    try:
        from getviews_pipeline.supabase_client import get_service_client

        sb = get_service_client()
    except Exception as exc:
        logger.warning("[pattern] service client unavailable: %s — empty state", exc)
        # Previously returned the @demo/"Stub video" fixture which leaked
        # placeholder evidence cards to production users (BUG-01, QA audit
        # 2026-04-22). The empty state is honest: no findings, no stubs.
        data = build_empty_pattern_report(window_days=eff_win)
        data["wow_diff"] = wow
        if subreports:
            data["subreports"] = _build_pattern_subreports(niche_id, query, eff_win, subreports)
        return data

    if step_queue is not None:
        from getviews_pipeline.step_events import (
            emit,
            step_done,
            step_status,
            step_tool_complete,
            step_tool_start,
        )

        emit(step_queue, step_status(1, "Đang quét kho video TikTok Việt Nam..."))
        emit(
            step_queue,
            step_tool_start("Tải kho video ngách...", 1, 0, tool="corpus"),
        )

    ctx = load_pattern_inputs(sb, niche_id, window_days)
    if ctx is None:
        if step_queue is not None:
            emit(step_queue, step_tool_complete(1, 0, 0, [], tool="corpus"))
        data = build_empty_pattern_report(window_days=eff_win)
        data["wow_diff"] = wow
        return data

    eff_win = int(ctx.get("effective_window_days") or eff_win)
    ni = ctx["ni"]
    he_rows: list[dict[str, Any]] = ctx["he_rows"]
    corpus: list[dict[str, Any]] = ctx["corpus"]
    niche_label = str(ctx["niche_label"])
    niche_label_for_steps = niche_label if niche_label else f"Niche {niche_id}"

    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_tool_complete, step_tool_start

        thumbs = _pattern_thumb_urls(corpus)
        emit(
            step_queue,
            step_tool_complete(1, 0, len(corpus), thumbs, tool="corpus"),
        )
        emit(
            step_queue,
            step_tool_start(
                f"Phân tích hook · {niche_label_for_steps}",
                1,
                1,
                tool="corpus",
            ),
        )

    sample_n = int(ni.get("sample_size") or 0)
    ranked = rank_hooks_for_pattern(he_rows)

    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_tool_complete

        emit(step_queue, step_tool_complete(1, 1, len(ranked), [], tool="corpus"))

    if niche_id <= 0 or sample_n < 30 or len(ranked) < 3:
        if step_queue is not None:
            from getviews_pipeline.step_events import (
                emit,
                step_done,
                step_status,
                step_tool_complete,
                step_tool_start,
            )

            emit(step_queue, step_status(2, "Đang tổng hợp pattern nổi bật..."))
            emit(step_queue, step_tool_start("Viết báo cáo pattern", 2, 0, tool="synthesis"))
            emit(step_queue, step_tool_complete(2, 0, 0, [], tool="synthesis"))
            emit(step_queue, step_done("Xong — đang hiển thị báo cáo..."))
        thin = build_thin_corpus_pattern_report(
            sample_size=sample_n,
            niche_label=niche_label,
            window_days=eff_win,
        )
        thin["wow_diff"] = wow
        if isinstance(thin.get("confidence"), dict):
            thin["confidence"]["freshness_hours"] = _freshness_hours_from_corpus(corpus)
        outlier_t = fetch_outlier_story(sb, niche_id, eff_win)
        if outlier_t is not None:
            thin["outlier_story"] = outlier_t.model_dump()
        if subreports:
            thin["subreports"] = _build_pattern_subreports(niche_id, query, eff_win, subreports)
        return thin

    org = float(ni.get("organic_avg_views") or 0)
    com = float(ni.get("commerce_avg_views") or 0)
    # 0.0 (not 1.0) when the niche has no view baseline at all:
    # _fmt_delta_pct renders baseline<=0 as an honest "+0%", whereas the old
    # 1.0 fallback produced absurd "+49,900%" deltas on unseeded niches
    # (audit 2026-06-10 M-4).
    baseline_views = org if org > 0 else (com if com > 0 else 0.0)

    _creator_sets: dict[str, set[str]] = defaultdict(set)
    for row in corpus:
        h = str(row.get("hook_type") or "")
        ch = str(row.get("creator_handle") or "")
        if h and ch:
            _creator_sets[h].add(ch)

    runner_ups: dict[str, str] = {}
    for i, r in enumerate(ranked[:3]):
        ht = str(r.get("hook_type") or "")
        if i + 1 < len(ranked):
            runner_ups[ht] = str(ranked[i + 1].get("hook_type") or "other")

    top3_hook_list = [str(r.get("hook_type") or "") for r in ranked[:3]]
    top3_types = set(top3_hook_list)
    top_labels = [_pattern_label_from_he_row(r) for r in ranked[:3]]
    micro_context = build_micro_context(corpus, top3_hook_list, top_n=5)
    creator_counts_str = ", ".join(
        f"{label}: {len(_creator_sets.get(ht, set()))} creator"
        for ht, label in zip(top3_hook_list, top_labels)
    )
    top_performers_str = build_top_performers_context(corpus, top3_hook_list, top_n=3)

    ab_pair = None
    top_hook_type = top3_hook_list[0] if top3_hook_list else ""
    if top_hook_type:
        ab_pair = find_ab_pair(corpus, top_hook_type, min_delta=5)
    ab_context = ""
    if ab_pair:
        ab_context = (
            f"A/B cùng creator: {ab_pair.creator_handle} — "
            f"hit ({ab_pair.hit.hook_type}, {ab_pair.hit.views:,} view) vs "
            f"flop ({ab_pair.flop.hook_type}, {ab_pair.flop.views:,} view) — "
            f"delta {ab_pair.delta}×. Có thể cite trong cross_pattern_synthesis."
        )

    stalled, stalled_reason = compute_what_stalled(
        he_rows, top3_types, baseline_views, creator_sets=_creator_sets
    )
    stalled_labels = [s.pattern for s in stalled] if stalled else []

    live_context = ""
    from getviews_pipeline.config import GEMINI_API_KEY
    from getviews_pipeline.live_search import (
        fetch_live_supplement,
        format_live_awemes_for_prompt,
        needs_live_search,
    )

    if GEMINI_API_KEY and needs_live_search(query, len(corpus)):
        loop = asyncio.new_event_loop()
        try:
            live_awemes = loop.run_until_complete(
                fetch_live_supplement(
                    query=query,
                    niche_label=niche_label,
                    top_hook_types=top3_hook_list,
                    corpus_count=len(corpus),
                    iteration_start=2,
                    step_queue=step_queue,
                )
            )
        finally:
            loop.close()
        live_context = format_live_awemes_for_prompt(live_awemes[:20])

    if step_queue is not None:
        from getviews_pipeline.step_events import (
            INTENT_STEP_LABELS,
            emit,
            step_process,
            step_status,
            step_tool_start,
        )

        emit(step_queue, step_status(3, "Đang tổng hợp pattern nổi bật..."))
        emit(step_queue, step_tool_start("Viết báo cáo pattern", 3, 0, tool="synthesis"))
        emit(step_queue, step_process(INTENT_STEP_LABELS["trend_spike"][2]))

    narr = fill_pattern_narrative(
        query=query,
        niche_label=niche_label,
        top_hook_labels=top_labels,
        stalled_hook_labels=stalled_labels,
        micro_context=micro_context,
        creator_counts_str=creator_counts_str,
        top_performers_str=top_performers_str,
        ab_context=ab_context,
        live_context=live_context,
        wow_diff=wow,
        corpus_size=len(corpus),
    )

    why_won = build_why_won_list(top_labels)
    insights = narr.get("hook_insights") or []
    generated_prereqs = narr.get("generated_prerequisites") or []
    findings = compute_findings(
        ranked,
        corpus,
        baseline_views,
        runner_ups,
        insights,
        why_won,
        generated_prereqs,
        creator_sets=_creator_sets,
    )

    cultural_framings = narr.get("cultural_framing") or []
    hook_narratives = narr.get("hook_narratives") or []
    why_it_works_list = narr.get("why_it_works") or []
    micro_patterns_list = narr.get("micro_patterns") or []
    for i, finding in enumerate(findings):
        updates: dict = {}
        if i < len(cultural_framings):
            raw = cultural_framings[i]
            updates["cultural_framing"] = "" if raw is None else str(raw)[:300]
        if i < len(hook_narratives):
            raw_n = hook_narratives[i]
            updates["narrative"] = str(raw_n)[:500] if raw_n else None
        if i < len(why_it_works_list):
            raw_w = why_it_works_list[i]
            updates["why_it_works"] = str(raw_w)[:350] if raw_w else None
        if i < len(micro_patterns_list):
            raw_m = micro_patterns_list[i]
            updates["micro_pattern"] = str(raw_m)[:220] if raw_m else None
        if updates:
            findings[i] = finding.model_copy(update=updates)

    cross_synthesis: list[str] = list(narr.get("cross_pattern_synthesis") or [])
    stalled_insights = narr.get("stalled_insights") or []
    stalled_models: list[Any] = []
    for i, sf in enumerate(stalled):
        ins = stalled_insights[i] if i < len(stalled_insights) else sf.insight
        stalled_models.append(sf.model_copy(update={"insight": ins[:200]}))

    win_hooks = top3_types
    evidence = pick_evidence_videos(corpus, win_hooks, limit=6)
    if len(evidence) < 6:
        all_hooks = {str(x.get("hook_type") or "") for x in corpus if x.get("hook_type")}
        evidence = pick_evidence_videos(corpus, all_hooks, limit=6)

    fresh_h = _freshness_hours_from_corpus(corpus)
    confidence = ConfidenceStrip(
        sample_size=sample_n,
        window_days=eff_win,
        niche_scope=niche_label,
        freshness_hours=fresh_h,
        intent_confidence="medium",
        what_stalled_reason=stalled_reason,
    )

    creators = {str(x.get("creator_handle") or "") for x in corpus if x.get("creator_handle")}
    sources = [
        SourceRow(
            kind="video",
            label="Kho video đã quét",
            count=len(corpus),
            sub=f"{len(creators)} creator · {eff_win}d",
        )
    ]

    # 2026-05-10 — Wave 2 PR #1: inject niche_insights Layer 0 data so
    # the UI can surface execution_tip as the "what to do next" slot
    # and insight_text as preamble context. Graceful-null if the Layer
    # 0 cron hasn't run for this niche.
    from getviews_pipeline.niche_insight_fetcher import fetch_niche_insight

    niche_insight = fetch_niche_insight(niche_id, client=sb)
    outlier_story = fetch_outlier_story(sb, niche_id, eff_win)

    payload = PatternPayload(
        confidence=confidence,
        wow_diff=WoWDiff(**wow) if isinstance(wow, dict) else WoWDiff(),
        tldr={
            "thesis": str(narr.get("thesis") or "")[:280],
            "callouts": [s.model_dump() for s in build_tldr_callouts(ni, window_days)],
        },
        findings=findings,
        what_stalled=stalled_models,
        evidence_videos=evidence if evidence else pick_evidence_videos(corpus, set(), limit=6),
        patterns=build_pattern_cells(
            ni,
            trending_sounds=ctx.get("trending_sounds"),
            sound_trends=ctx.get("sound_trends"),
        ),
        actions=static_action_cards(baseline_views),
        sources=sources,
        related_questions=list(narr.get("related_questions") or [])[:4],
        subreports=(
            _build_pattern_subreports(niche_id, query, eff_win, subreports)
            if subreports
            else None
        ),
        niche_insight=niche_insight,
        outlier_story=outlier_story,
        cross_pattern_synthesis=cross_synthesis,
        ab_pair=ab_pair,
    )
    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_done, step_tool_complete

        emit(step_queue, step_tool_complete(3, 0, 0, [], tool="synthesis"))
        emit(step_queue, step_done("Xong — đang hiển thị báo cáo..."))
    return payload.model_dump()


def _build_pattern_subreports(
    niche_id: int,
    query: str,
    window_days: int,
    subreports: list[str],
) -> dict[str, Any] | None:
    """Dispatch declared subreports to their respective builders.

    Today only ``"timing"`` is auto-merged (C.5.3 §A.4 Report + timing case).
    Unknown subreport keys are logged and dropped rather than failing the
    whole turn — Pattern is the primary, subreports are nice-to-have.
    Returns ``None`` when no subreports were built so the pydantic model
    serialises ``subreports: null`` rather than ``{}`` (UI hides the block).
    """
    out: dict[str, Any] = {}
    for key in subreports:
        if key == "timing":
            try:
                from getviews_pipeline.report_timing import build_timing_report

                out["timing"] = build_timing_report(niche_id, query, window_days=window_days)
            except Exception as exc:
                logger.warning("[pattern] timing subreport failed: %s — skipping", exc)
        else:
            logger.warning("[pattern] unknown subreport key %r — skipping", key)
    return out if out else None


def _pattern_label_from_he_row(r: dict[str, Any]) -> str:
    from getviews_pipeline.script_data import HOOK_TYPE_PATTERN_VI

    ht = str(r.get("hook_type") or "")
    key = ht.strip().lower().replace("-", "_")
    return HOOK_TYPE_PATTERN_VI.get(key, ht.replace("_", " ").title() or "Hook")
