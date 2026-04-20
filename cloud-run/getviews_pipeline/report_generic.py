"""Phase C.5 — Generic humility report.

Design source: ``artifacts/uiux-reference/screens/thread-turns.jsx`` lines
364–388 (GenericTurn). New §J sections over the reference:

- ``ConfidenceStrip.intent_confidence == "low"`` — pinned so the UI
  can render a FALLBACK chip.
- ``off_taxonomy.suggestions[3]`` — static routes that unclassifiable
  queries should try instead of asking again.
- Length cap on ``narrative.paragraphs[]`` (≤ 2 entries, ≤ 320 chars
  each). Enforced by ``report_generic_compute.cap_paragraphs`` — the
  pydantic model does not add a validator because the fallback path
  must always produce a payload, truncation is non-fatal.

Generic is always free (C.0.5 credit rule): the caller skips
``decrement_credit`` for ``kind == "generic"`` and for
``follow_up_unclassifiable`` downgrades. This module returns a
validated ``GenericPayload`` and nothing more.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.report_generic_compute import (
    _tile_color_for,
    build_off_taxonomy_payload,
    cap_paragraphs,
    pick_broad_evidence,
)
from getviews_pipeline.report_types import (
    ConfidenceStrip,
    EvidenceCardPayload,
    GenericPayload,
    SourceRow,
    validate_and_store_report,
)

logger = logging.getLogger(__name__)


# ── Fixture path (C.1.2) ────────────────────────────────────────────────────


def build_fixture_generic_report(query: str = "câu hỏi chung") -> dict[str, Any]:
    """Full fixture — validates against §J `GenericPayload`."""
    confidence = ConfidenceStrip(
        sample_size=18,
        window_days=14,
        niche_scope=None,  # Generic clears niche scope — fallback is broad.
        freshness_hours=12,
        intent_confidence="low",
    )
    narrative = cap_paragraphs(
        [
            (
                f"Câu hỏi «{query[:120]}» ngoài taxonomy — Studio không đủ tín hiệu "
                f"để xếp hạng. Dựa trên corpus rộng 18 video 14 ngày qua, đây là "
                f"hướng gần đúng; nên thử công cụ chuyên biệt bên dưới."
            ),
            (
                "Nếu bạn đang tìm insight theo kênh, pattern cụ thể, hoặc brief cho "
                "tuần tới — ba chip bên dưới đi thẳng đến nơi cần."
            ),
        ]
    )
    ev = [
        EvidenceCardPayload(
            video_id=f"g{i}",
            creator_handle=f"@creator_{i}",
            title=f"Video mẫu {i}",
            views=80_000 - i * 7_000,
            retention=0.52,
            duration_sec=28,
            bg_color=_tile_color_for(i),
            hook_family="talking_head",
        )
        for i in range(3)
    ]
    payload = GenericPayload(
        confidence=confidence,
        off_taxonomy=build_off_taxonomy_payload(),
        narrative={"paragraphs": narrative},
        evidence_videos=ev,
        sources=[SourceRow(kind="datapoint", label="Corpus (broad)", count=18, sub="14d")],
        related_questions=[
            "Hỏi theo niche cụ thể?",
            "Dán link video để Soi Video?",
            "Dán @handle để Soi Kênh?",
        ],
    )
    return payload.model_dump()


ANSWER_FIXTURE_GENERIC: dict[str, Any] = validate_and_store_report(
    "generic",
    build_fixture_generic_report(),
)


# ── Live pipeline (C.5.1) ──────────────────────────────────────────────────


def build_generic_report(
    niche_id: int | None,
    query: str,
    *,
    intent_confidence: str = "low",  # noqa: ARG001 — reserved for telemetry
    window_days: int = 14,
) -> dict[str, Any]:
    """Live Generic report. Falls back to fixture when DB / niche unavailable.

    Always emits:
    - ``intent_confidence = "low"`` on the confidence strip (Generic IS the
      low-confidence landing; frontend renders FALLBACK chip).
    - 3 `OFF_TAXONOMY_SUGGESTIONS` chips.
    - 1–2 Gemini-bounded paragraphs capped at 320 chars each.
    - 3 broad-evidence tiles sorted by views desc.

    Never raises — the fallback path must always surface a payload so the
    UI can render the OffTaxonomyBanner + suggestions.
    """
    try:
        from getviews_pipeline.supabase_client import get_service_client

        sb = get_service_client()
    except Exception as exc:
        logger.warning("[generic] service client unavailable: %s — fixture path", exc)
        inner = build_fixture_generic_report(query=query)
        if isinstance(inner.get("confidence"), dict):
            inner["confidence"]["window_days"] = window_days
        return inner

    corpus = _load_broad_corpus(sb, niche_id, window_days)
    sample_n = len(corpus)
    evidence_rows = pick_broad_evidence(corpus, limit=3)
    evidence = [_corpus_row_to_evidence(r, i) for i, r in enumerate(evidence_rows)]
    if not evidence:
        inner = build_fixture_generic_report(query=query)
        if isinstance(inner.get("confidence"), dict):
            inner["confidence"]["window_days"] = window_days
        return inner

    niche_label = _niche_label(sb, niche_id) if niche_id else None

    paras = _generate_narrative(
        query=query,
        niche_label=niche_label,
        sample_n=sample_n,
        window_days=window_days,
    )
    paras = cap_paragraphs(paras)

    payload = GenericPayload(
        confidence=ConfidenceStrip(
            sample_size=sample_n,
            window_days=window_days,
            niche_scope=None,  # Generic never claims a niche scope
            freshness_hours=_freshness_hours(corpus),
            intent_confidence="low",
        ),
        off_taxonomy=build_off_taxonomy_payload(),
        narrative={"paragraphs": paras},
        evidence_videos=evidence,
        sources=[
            SourceRow(
                kind="datapoint",
                label="Corpus (broad)",
                count=sample_n,
                sub=(niche_label or "đa ngách") + f" · {window_days}d",
            )
        ],
        related_questions=[
            "Hỏi theo niche cụ thể?",
            "Dán link video để Soi Video?",
            "Dán @handle để Soi Kênh?",
        ],
    )
    return payload.model_dump()


# ── Narrative generation — Gemini with hedging fallback ────────────────────


def _generate_narrative(
    *,
    query: str,
    niche_label: str | None,
    sample_n: int,
    window_days: int,
) -> list[str]:
    """Bounded Gemini narrative with explicit hedging fallback.

    Gemini failure / unavailability returns a deterministic hedge so the
    humility landing still ships copy. Both paths go through
    ``cap_paragraphs`` before the payload is validated.
    """
    try:
        from getviews_pipeline.report_generic_gemini import fill_generic_narrative

        paras = fill_generic_narrative(
            query=query,
            niche_label=niche_label,
            sample_n=sample_n,
            window_days=window_days,
        )
        if paras:
            return paras
    except Exception as exc:
        logger.info("[generic] Gemini narrative skipped: %s", exc)

    scope = niche_label or "corpus rộng"
    return [
        (
            f"Câu hỏi «{query[:140]}» ngoài taxonomy — Studio không đủ tín hiệu "
            f"để phân loại. Dựa trên {sample_n} video trong {scope} {window_days} "
            f"ngày qua, đây là hướng gần đúng."
        ),
        "Gợi ý: mở công cụ chuyên biệt bên dưới để có kết quả đáng tin cậy hơn.",
    ]


# ── DB helpers ─────────────────────────────────────────────────────────────


def _load_broad_corpus(sb: Any, niche_id: int | None, window_days: int) -> list[dict[str, Any]]:
    """Load a broad slice for evidence tiles. Niche-scoped when ``niche_id``
    is provided, otherwise cross-niche (respects RLS — service client only
    sees niches the caller is authorised for via the outer endpoint)."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max(window_days, 14))).isoformat()
        q = (
            sb.table("video_corpus")
            .select(
                "video_id, creator_handle, views, hook_type, engagement_rate, "
                "video_duration, analysis_json, caption, thumbnail_url, indexed_at, created_at"
            )
            .gte("indexed_at", cutoff)
            .order("views", desc=True)
            .limit(200)
        )
        if niche_id:
            q = q.eq("niche_id", niche_id)
        res = q.execute()
        return list(res.data or [])
    except Exception as exc:
        logger.warning("[generic] broad corpus fetch failed: %s", exc)
        return []


def _niche_label(sb: Any, niche_id: int) -> str | None:
    try:
        res = (
            sb.table("niche_taxonomy")
            .select("name_vn, name_en")
            .eq("id", niche_id)
            .maybe_single()
            .execute()
        )
        row = res.data or {}
        return str(row.get("name_vn") or row.get("name_en") or "")
    except Exception:
        return None


def _corpus_row_to_evidence(row: dict[str, Any], idx: int) -> EvidenceCardPayload:
    vid = str(row.get("video_id") or f"g-{idx}")
    er = float(row.get("engagement_rate") or 0)
    retention = min(0.99, er / 100.0) if er > 1.0 else min(0.99, max(0.0, er))
    dur = int(float(row.get("video_duration") or 0) or 0)
    if dur <= 0:
        aj = row.get("analysis_json") or {}
        if isinstance(aj, str):
            import json

            try:
                aj = json.loads(aj)
            except Exception:
                aj = {}
        if isinstance(aj, dict):
            dur = int(float(aj.get("duration_seconds") or 0) or 0)
    thumb = str(row.get("thumbnail_url") or "").strip()
    return EvidenceCardPayload(
        video_id=vid,
        creator_handle=str(row.get("creator_handle") or "@unknown"),
        title=str(row.get("caption") or "Video")[:120],
        views=int(row.get("views") or 0),
        retention=retention,
        duration_sec=max(1, dur),
        bg_color=_tile_color_for(idx),
        hook_family=str(row.get("hook_type") or "other"),
        thumbnail_url=thumb or None,
    )


def _freshness_hours(corpus: list[dict[str, Any]]) -> int:
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
