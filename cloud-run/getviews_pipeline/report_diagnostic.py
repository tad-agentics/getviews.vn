"""Phase C.6 — Diagnostic report aggregator (fixture + live pipeline stub).

Serves exactly one intent:

  - ``own_flop_no_url`` — "my last video flopped and I don't have the link"

This intent used to route to ``answer:pattern`` (niche hook leaderboard),
which was off-topic. The diagnostic template is scoped down from Claude
Chat's Report 4 (VIDEO DIAGNOSIS): 5 fixed failure-mode categories with
a confidence-weighted verdict (``likely_issue`` / ``possible_issue`` /
``unclear`` / ``probably_fine``) — NOT a numeric score, because we
don't have the video itself.

See ``artifacts/docs/report-template-prd-diagnostic.md``.

Live pipeline (Gemini narrative + benchmark loading) lands in commit 4c.
This module currently ships the fixture + the stub live entrypoint so
the dispatcher wiring in commit 4b can import the helper safely.
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


# ── Live pipeline (stub — replaced in commit 4c) ────────────────────────────


def build_diagnostic_report(
    niche_id: int,  # noqa: ARG001 — wired in commit 4c
    query: str,
    window_days: int = 14,  # noqa: ARG001 — wired in commit 4c
) -> dict[str, Any]:
    """Live URL-less flop diagnostic. STUB — returns the fixture until
    the Gemini-powered live pipeline lands on this branch.

    Signature is final so commit 4b can import + wire the dispatcher,
    and commit 4c replaces only the body (benchmark loader + Gemini
    narrative + fallback).
    """
    logger.info(
        "[diagnostic] fixture stub niche=%s query_len=%s (live pipeline pending)",
        niche_id, len(query or ""),
    )
    return build_fixture_diagnostic_report(query)
