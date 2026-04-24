"""Phase C.6 — Diagnostic report aggregator (fixture + live pipeline).

Serves exactly one intent:

  - ``own_flop_no_url`` — "my last video flopped and I don't have the link"

This intent used to route to ``answer:pattern`` (niche hook leaderboard),
which was off-topic. The diagnostic template is scoped down from Claude
Chat's Report 4 (VIDEO DIAGNOSIS): 5 fixed failure-mode categories with
a confidence-weighted verdict (``likely_issue`` / ``possible_issue`` /
``unclear`` / ``probably_fine``) — NOT a numeric score, because we
don't have the video itself.

See ``artifacts/docs/report-template-prd-diagnostic.md``.

Live pipeline (commit 4c): load niche benchmarks from ``niche_intelligence``,
call ``report_diagnostic_gemini.fill_diagnostic_narrative`` to map the
user's symptoms onto the 5 category verdicts + 2-3 prescriptions,
validate, and return. Fallback paths (no Supabase client, no Gemini,
empty query) all converge on a deterministic "5 unclear + paste-link"
shape — the "honesty" invariant.
"""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.report_types import (
    ConfidenceStrip,
    DiagnosticCategory,
    DiagnosticPayload,
    DiagnosticPrescription,
    SourceRow,
    validate_and_store_report,
)

logger = logging.getLogger(__name__)


# ── Fixed category contract ────────────────────────────────────────────────
#
# The 5 category names are a hard contract pinned by position on the
# frontend (Hook / Pacing / CTA / Sound / Caption+Hashtag). Don't
# reorder without coordinating the DiagnosticBody render.

DIAGNOSTIC_CATEGORY_NAMES: tuple[str, str, str, str, str] = (
    "Hook (0–3s)",
    "Pacing (3–20s)",
    "CTA",
    "Sound",
    "Caption & Hashtag",
)


# ── Fixture path ────────────────────────────────────────────────────────────


def _fixture_categories() -> list[DiagnosticCategory]:
    """5 categories that exercise all 4 verdict types — for schema tests."""
    return [
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[0],
            verdict="likely_issue",
            finding=(
                "Bạn mô tả 'không ai xem hết video' và 'mở đầu hơi lan man' — "
                "hook kéo dài quá 1.2s dễ mất người xem ngay trong 3s đầu."
            ),
            fix_preview="Rút hook về ≤ 1.2 giây; mở bằng câu hỏi chốt, không giới thiệu.",
        ),
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[1],
            verdict="possible_issue",
            finding=(
                "Ngách Skincare median tps 1.4; nếu video bạn < 1.2 tps thì "
                "retention 3–20s sẽ rơi mạnh. Cần xem frame để kết luận."
            ),
            fix_preview="Cắt mỗi scene xuống 2–3 giây; thêm text overlay mỗi beat.",
        ),
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[2],
            verdict="unclear",
            finding=(
                "Không rõ CTA cuối video là dạng nào (follow / comment / save) "
                "từ mô tả — cần link để chấm điểm chính xác phần này."
            ),
            fix_preview=None,
        ),
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[3],
            verdict="possible_issue",
            finding=(
                "Audio trending trong 4 tuần gần nhất được dùng bởi top-5 "
                "creator Skincare. Video cũ nếu đang dùng audio original có "
                "thể thiếu đẩy thuật toán."
            ),
            fix_preview="Đổi sang top-5 sound Skincare trending tuần này.",
        ),
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[4],
            verdict="probably_fine",
            finding=(
                "Bạn đã nhắc đến ngách + tag cụ thể; phần caption+hashtag "
                "thường không phải nguyên nhân chính khi retention < 40%."
            ),
            fix_preview=None,
        ),
    ]


def _fixture_prescriptions() -> list[DiagnosticPrescription]:
    """3 ranked prescriptions matching the top 3 categories by verdict urgency."""
    return [
        DiagnosticPrescription(
            priority="P1",
            action="Viết lại hook — chốt trong 1.2s đầu, bỏ câu giới thiệu.",
            impact="Dự báo: +12–18 điểm retention trong 3s đầu.",
            effort="low",
        ),
        DiagnosticPrescription(
            priority="P2",
            action="Tăng pacing — cắt scene xuống ≤ 3 giây + text overlay theo beat.",
            impact="Dự báo: giảm drop-off tại 5–10s khoảng 8–12%.",
            effort="medium",
        ),
        DiagnosticPrescription(
            priority="P3",
            action="Đổi audio sang top-5 trending Skincare tuần này.",
            impact="Dự báo: tăng cơ hội vào discovery feed ngách.",
            effort="low",
        ),
    ]


def build_fixture_diagnostic_report(query: str = "") -> dict[str, Any]:
    """Reference-shape fixture payload. Threading ``query`` is a no-op
    today (fixture strings are static), but commit 4c replaces the cells
    via Gemini and honours the query end-to-end.

    Used by pytest (schema validation) + frontend dev harnesses. The live
    pipeline will swap categories + prescriptions per request while
    keeping this 5-category contract intact.
    """
    payload = DiagnosticPayload(
        confidence=ConfidenceStrip(
            # Diagnostic confidence is capped at "medium" — we don't have
            # the video itself, so we never claim "high".
            sample_size=240,
            window_days=14,
            niche_scope="Skincare & Làm Đẹp",
            freshness_hours=6,
            intent_confidence="medium",
        ),
        framing=(
            "Chưa có link video — mình chẩn đoán dựa trên mô tả và "
            "benchmark ngách."
        ),
        categories=_fixture_categories(),
        prescriptions=_fixture_prescriptions(),
        sources=[
            SourceRow(
                kind="datapoint",
                label="Benchmark ngách",
                count=240,
                sub="Skincare · 14d",
            ),
        ],
        related_questions=[
            "Nếu paste link, báo cáo có thay đổi thế nào?",
            "Video < 10K follower có nên ưu tiên hook hay pacing?",
            "Dùng sound trending có giúp video cũ phục hồi không?",
        ],
    )
    return payload.model_dump()


ANSWER_FIXTURE_DIAGNOSTIC: dict[str, Any] = validate_and_store_report(
    "diagnostic", build_fixture_diagnostic_report(),
)


# ── Benchmark loader ───────────────────────────────────────────────────────


def _load_niche_benchmarks(
    sb: Any,
    niche_id: int,
) -> tuple[str | None, dict[str, Any]]:
    """Return ``(niche_label, benchmarks_dict)``.

    Reads ``niche_taxonomy`` for the display label, plus a best-effort
    ``niche_intelligence`` row for avg retention / median tps / top
    sound / common CTA types. Every field is optional — sparse rows
    simply trim the prompt context.

    Fails open: any DB error returns ``(None, {})`` so the builder can
    still fall back to the deterministic unclear path.
    """
    label: str | None = None
    bm: dict[str, Any] = {}

    try:
        nt = (
            sb.table("niche_taxonomy")
            .select("name_vn, name_en")
            .eq("id", niche_id)
            .maybe_single()
            .execute()
        )
        row = nt.data or {}
        label = str(row.get("name_vn") or row.get("name_en") or "") or None
    except Exception as exc:
        logger.warning("[diagnostic] niche_taxonomy fetch failed: %s", exc)

    try:
        ni = (
            sb.table("niche_intelligence")
            .select("avg_retention, median_tps, top_sound, common_cta_types")
            .eq("niche_id", niche_id)
            .maybe_single()
            .execute()
        )
        ni_row = ni.data or {}
        for k in ("avg_retention", "median_tps", "top_sound", "common_cta_types"):
            if ni_row.get(k) is not None:
                bm[k] = ni_row[k]
    except Exception as exc:
        # niche_intelligence is optional enrichment — log and continue.
        logger.info("[diagnostic] niche_intelligence skipped: %s", exc)

    return label, bm


def _fetch_niche_execution_tip(sb: Any, niche_id: int) -> str | None:
    """Return the current week's ``execution_tip`` for a niche, or None.

    Sister helper to ``pipelines._get_niche_insight``, but returns JUST
    the execution_tip field (no wrapping prompt block) so the value can
    surface on ``DiagnosticPayload.niche_execution_tip`` without
    Gemini's prompt context leaking into the user-visible payload.

    Fails open: any DB error / empty table → None, frontend hides the
    surface. Skips rows flagged by the Layer 0 quality guard.
    """
    try:
        resp = (
            sb.table("niche_insights")
            .select("execution_tip")
            .eq("niche_id", niche_id)
            .is_("quality_flag", None)
            .order("week_of", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        # niche_insights is optional — sparse-niche empty state is fine.
        logger.info("[diagnostic] niche_execution_tip skipped: %s", exc)
        return None
    rows = resp.data or []
    if not rows:
        return None
    tip = (rows[0].get("execution_tip") or "").strip()
    # DiagnosticPayload caps at 240 chars. Pre-trim here so Pydantic
    # validation never rejects a long tip — any trailing context is
    # Layer 0 prose the frontend would truncate anyway.
    if len(tip) > 240:
        tip = tip[:237].rstrip() + "…"
    return tip or None


# ── Live pipeline ───────────────────────────────────────────────────────────


def build_diagnostic_report(
    niche_id: int,
    query: str,
    window_days: int = 14,
) -> dict[str, Any]:
    """Live URL-less flop diagnostic.

    Flow:
      1. Load niche label + benchmarks (best-effort; continues on any
         error so budget exhaustion / DB blip doesn't break the turn).
      2. Call ``fill_diagnostic_narrative`` for the Gemini-generated
         framing + 5 category verdicts + 1-3 prescriptions.
      3. Assemble ``DiagnosticPayload``, validate, return the inner
         dict (``append_turn`` wraps with ``validate_and_store_report``).

    Fallback paths (all produce valid payloads):
      - Supabase client unavailable → ``_fallback_payload`` with
        deterministic "5 unclear" shape.
      - Empty / short query → narrative module refuses Gemini, returns
        "5 unclear" + paste-link prescription.
      - Gemini exception → narrative module falls back; builder still
        ships.
    """
    try:
        from getviews_pipeline.supabase_client import get_service_client

        sb = get_service_client()
    except Exception as exc:
        logger.warning("[diagnostic] service client unavailable: %s — fallback", exc)
        return _fallback_payload(query=query, window_days=window_days)

    niche_label, benchmarks = _load_niche_benchmarks(sb, niche_id)
    niche_execution_tip = _fetch_niche_execution_tip(sb, niche_id)

    from getviews_pipeline.report_diagnostic_gemini import fill_diagnostic_narrative

    narrative = fill_diagnostic_narrative(
        query=query,
        niche_label=niche_label or "TikTok Việt Nam",
        benchmarks=benchmarks,
    )

    # confidence intent_confidence stays capped at medium even when we
    # have a query — no video = no "high" confidence.
    confidence_level: str = "medium" if (query or "").strip() else "low"

    categories = [DiagnosticCategory(**c) for c in narrative["categories"]]
    prescriptions = [DiagnosticPrescription(**p) for p in narrative["prescriptions"]]

    try:
        payload = DiagnosticPayload(
            confidence=ConfidenceStrip(
                sample_size=benchmarks.get("sample_size") or 0,
                window_days=window_days,
                niche_scope=niche_label or "TikTok Việt Nam",
                freshness_hours=24,
                intent_confidence=confidence_level,  # type: ignore[arg-type]
            ),
            framing=narrative["framing"],
            categories=categories,
            prescriptions=prescriptions,
            sources=[
                SourceRow(
                    kind="datapoint",
                    label="Benchmark ngách",
                    count=benchmarks.get("sample_size") or 0,
                    sub=f"{niche_label or 'TikTok Việt Nam'} · {window_days}d",
                ),
            ],
            related_questions=_related_questions(query, niche_label),
            niche_execution_tip=niche_execution_tip,
        )
    except Exception as exc:
        logger.warning(
            "[diagnostic] payload validation failed: %s — fallback", exc,
        )
        return _fallback_payload(
            query=query,
            window_days=window_days,
            niche_label=niche_label,
            niche_execution_tip=niche_execution_tip,
        )

    return payload.model_dump()


def _related_questions(query: str, niche_label: str | None) -> list[str]:
    """3 query-aware follow-ups. Deterministic (no Gemini call) so this
    slot doesn't double the latency budget of the report."""
    niche = niche_label or "ngách của bạn"
    q_clean = (query or "").strip()
    if q_clean:
        first = f"Nếu paste link, chẩn đoán «{q_clean[:60]}» sẽ khác thế nào?"
    else:
        first = "Nếu paste link, chẩn đoán có đổi nhiều không?"
    return [
        first,
        f"Video < 10K follower trong {niche} ưu tiên hook hay pacing?",
        "Đổi sound trending có giúp video cũ phục hồi không?",
    ]


def _fallback_payload(
    *,
    query: str,
    window_days: int,
    niche_label: str | None = None,
    niche_execution_tip: str | None = None,
) -> dict[str, Any]:
    """Deterministic "5 unclear + paste-link" payload — the honesty
    fallback used when the service client, Gemini, or payload assembly
    fails. Still validates cleanly through ``DiagnosticPayload``.

    ``niche_execution_tip`` is forwarded when the caller already
    fetched it (live pipeline → validation-error branch). Defaults to
    None when the fallback runs without ever touching the DB.
    """
    from getviews_pipeline.report_diagnostic_gemini import fill_diagnostic_narrative

    narrative = fill_diagnostic_narrative(
        query=query,
        niche_label=niche_label or "TikTok Việt Nam",
        benchmarks={},
    )
    categories = [DiagnosticCategory(**c) for c in narrative["categories"]]
    prescriptions = [DiagnosticPrescription(**p) for p in narrative["prescriptions"]]

    payload = DiagnosticPayload(
        confidence=ConfidenceStrip(
            sample_size=0,
            window_days=window_days,
            niche_scope=niche_label or "TikTok Việt Nam",
            freshness_hours=24,
            intent_confidence="low",
        ),
        framing=narrative["framing"],
        categories=categories,
        prescriptions=prescriptions,
        sources=[
            SourceRow(
                kind="datapoint",
                label="Benchmark ngách",
                count=0,
                sub=f"{niche_label or 'TikTok Việt Nam'} · {window_days}d",
            ),
        ],
        related_questions=_related_questions(query, niche_label),
        niche_execution_tip=niche_execution_tip,
    )
    return payload.model_dump()
