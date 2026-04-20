"""Phase C.2 — Pattern report aggregator (fixture + live pipeline hook)."""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.report_types import (
    ActionCardPayload,
    ConfidenceStrip,
    ContrastAgainst,
    EvidenceCardPayload,
    HookFinding,
    Lifecycle,
    Metric,
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
    )
    return payload.model_dump()


# C.1.2 — full §J `ReportV1` envelope for pytest / smoke scripts (`kind` + `report`).
ANSWER_FIXTURE_PATTERN: dict[str, Any] = validate_and_store_report(
    "pattern",
    build_fixture_pattern_report(),
)


def build_thin_corpus_pattern_report(*, sample_size: int = 12) -> dict[str, Any]:
    """Thin-corpus shape: N<30, humility reason, no stalled rows (C.2.1 pytest contract).

    ``sample_size`` defaults to 12 for standalone/fixture use. The live pipeline passes
    the real ``niche_intelligence.sample_size`` so the UI shows the actual corpus count.
    """
    inner = build_fixture_pattern_report()
    conf = inner["confidence"]
    if isinstance(conf, dict):
        conf["sample_size"] = max(0, int(sample_size))
        conf["what_stalled_reason"] = "ngách quá thưa — không đủ hook để xếp hạng âm"
    inner["tldr"] = {
        "thesis": "Mẫu nhỏ: chỉ dùng để định hướng, không kết luận toàn ngách.",
        "callouts": inner["tldr"].get("callouts", []),
    }
    return inner


def _freshness_hours_from_corpus(corpus: list[dict[str, Any]]) -> int:
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


def build_pattern_report(
    niche_id: int,
    query: str,
    _intent_type: str,
    window_days: int = 7,
    *,
    subreports: list[str] | None = None,
) -> dict[str, Any]:
    """C.2.2 — live pattern report: DB aggregators + optional Gemini copy + WoW merge.

    C.5.3 — ``subreports`` attaches auxiliary payloads under ``payload.subreports``
    (e.g. ``{"timing": TimingPayload}``). Only ``"timing"`` is supported today;
    unknown keys are ignored with a ``[pattern]`` warning.
    """
    wow = wow_rows_to_wow_diff(fetch_pattern_wow_diff_rows(niche_id)).model_dump()

    try:
        from getviews_pipeline.supabase_client import get_service_client

        sb = get_service_client()
    except Exception as exc:
        logger.warning("[pattern] service client unavailable: %s — fixture path", exc)
        data = build_fixture_pattern_report()
        if isinstance(data.get("confidence"), dict):
            data["confidence"]["window_days"] = window_days
        data["wow_diff"] = wow
        if subreports:
            data["subreports"] = _build_pattern_subreports(niche_id, query, window_days, subreports)
        return data

    from getviews_pipeline.report_pattern_compute import (
        build_pattern_cells,
        build_tldr_callouts,
        compute_findings,
        compute_what_stalled,
        load_pattern_inputs,
        pick_evidence_videos,
        rank_hooks_for_pattern,
        static_action_cards,
    )
    from getviews_pipeline.report_pattern_gemini import build_why_won_list, fill_pattern_narrative

    ctx = load_pattern_inputs(sb, niche_id, window_days)
    if ctx is None:
        data = build_fixture_pattern_report()
        if isinstance(data.get("confidence"), dict):
            data["confidence"]["window_days"] = window_days
        data["wow_diff"] = wow
        return data

    ni = ctx["ni"]
    he_rows: list[dict[str, Any]] = ctx["he_rows"]
    corpus: list[dict[str, Any]] = ctx["corpus"]
    niche_label = str(ctx["niche_label"])

    sample_n = int(ni.get("sample_size") or 0)
    ranked = rank_hooks_for_pattern(he_rows)
    if niche_id <= 0 or sample_n < 30 or len(ranked) < 3:
        thin = build_thin_corpus_pattern_report(sample_size=sample_n)
        thin["wow_diff"] = wow
        if isinstance(thin.get("confidence"), dict):
            thin["confidence"]["window_days"] = window_days
            thin["confidence"]["niche_scope"] = niche_label
            thin["confidence"]["freshness_hours"] = _freshness_hours_from_corpus(corpus)
        return thin

    org = float(ni.get("organic_avg_views") or 0)
    com = float(ni.get("commerce_avg_views") or 0)
    baseline_views = org if org > 0 else (com if com > 0 else 1.0)

    runner_ups: dict[str, str] = {}
    for i, r in enumerate(ranked[:3]):
        ht = str(r.get("hook_type") or "")
        if i + 1 < len(ranked):
            runner_ups[ht] = str(ranked[i + 1].get("hook_type") or "other")

    top3_types = {str(r.get("hook_type") or "") for r in ranked[:3]}
    top_labels = [_pattern_label_from_he_row(r) for r in ranked[:3]]

    stalled, stalled_reason = compute_what_stalled(he_rows, top3_types, baseline_views)
    stalled_labels = [s.pattern for s in stalled] if stalled else []

    narr = fill_pattern_narrative(
        query=query,
        niche_label=niche_label,
        top_hook_labels=top_labels,
        stalled_hook_labels=stalled_labels,
    )

    why_won = build_why_won_list(top_labels)
    insights = narr.get("hook_insights") or []
    findings = compute_findings(
        ranked,
        corpus,
        baseline_views,
        runner_ups,
        insights,
        why_won,
    )

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
        window_days=window_days,
        niche_scope=niche_label,
        freshness_hours=fresh_h,
        intent_confidence="medium",
        what_stalled_reason=stalled_reason,
    )

    creators = {str(x.get("creator_handle") or "") for x in corpus if x.get("creator_handle")}
    sources = [
        SourceRow(
            kind="video",
            label="Corpus quét",
            count=len(corpus),
            sub=f"{len(creators)} creator · {window_days}d",
        )
    ]

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
        patterns=build_pattern_cells(ni),
        actions=static_action_cards(baseline_views),
        sources=sources,
        related_questions=list(narr.get("related_questions") or [])[:4],
        subreports=(
            _build_pattern_subreports(niche_id, query, window_days, subreports)
            if subreports
            else None
        ),
    )
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
