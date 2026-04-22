"""Phase C.5 — Lifecycle report aggregator (fixture + live pipeline).

Serves three intents that were previously force-fit into the pattern
template (QA audit 2026-04-22, see ``artifacts/docs/report-templates-
audit.md``):

  - ``format_lifecycle_optimize`` — "format X còn chạy được nữa không?"
  - ``fatigue``                   — "hook này còn hiệu quả không?"
  - ``subniche_breakdown``        — "ngách con nào đang nổi?"

All three share one rendering primitive: a ranked list of cells, each
with a lifecycle stage pill + reach delta + health score + insight.
The payload ``mode`` discriminator tells the frontend which header copy
+ supplementary fields to show.

This module currently ships the fixture builders (full-sample payload +
thin-corpus variant) and ``ANSWER_FIXTURE_LIFECYCLE`` so pytest /
frontend dev harnesses have a validated shape to work with. The live
pipeline (Gemini narrative + corpus aggregates per mode) lands in a
follow-up commit on this same branch; callers using ``build_lifecycle_
report`` today get the fixture-shaped empty state.
"""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.report_types import (
    ActionCardPayload,
    ConfidenceStrip,
    LifecycleCell,
    LifecycleMode,
    LifecyclePayload,
    RefreshMove,
    SourceRow,
    validate_and_store_report,
)

logger = logging.getLogger(__name__)


# ── Fixture path ────────────────────────────────────────────────────────────


def _fixture_cells_format() -> list[LifecycleCell]:
    """Four format-lifecycle cells matching the reference design."""
    return [
        LifecycleCell(
            name="Short-form 15–30s",
            stage="rising",
            reach_delta_pct=28.0,
            health_score=82,
            retention_pct=73.0,
            insight="Đang tăng trưởng ổn định — format chính để discovery trong ngách.",
        ),
        LifecycleCell(
            name="Medium-form 30–60s",
            stage="peak",
            reach_delta_pct=12.0,
            health_score=74,
            retention_pct=68.0,
            insight="Đỉnh hiệu quả. Vẫn tốt nhưng sắp bước vào cao nguyên.",
        ),
        LifecycleCell(
            name="Carousel ảnh",
            stage="plateau",
            reach_delta_pct=3.0,
            health_score=58,
            retention_pct=51.0,
            insight="Không còn tăng trưởng. Chỉ dùng khi nội dung cần so sánh trực quan.",
        ),
        LifecycleCell(
            name="Long-form 60s+",
            stage="declining",
            reach_delta_pct=-8.0,
            health_score=41,
            retention_pct=44.0,
            insight="Đang giảm. Thuật toán ưu tiên content ngắn trong ngách này.",
        ),
    ]


def _fixture_cells_hook_fatigue() -> list[LifecycleCell]:
    """Single-hook fatigue shape: focus cell + 2 comparable hooks as context."""
    return [
        LifecycleCell(
            name="Hook 'Mình vừa test ___'",
            stage="declining",
            reach_delta_pct=-18.0,
            health_score=38,
            insight="Giảm 18% trong 4 tuần — hook đã được dùng bởi 1.2K creator trong ngách.",
        ),
        LifecycleCell(
            name="Hook 'Không ai nói với bạn'",
            stage="rising",
            reach_delta_pct=14.0,
            health_score=72,
            insight="Vẫn đang lên — cùng họ curiosity-gap nhưng chưa bão hoà.",
        ),
        LifecycleCell(
            name="Hook 'POV bạn vừa phát hiện'",
            stage="peak",
            reach_delta_pct=4.0,
            health_score=64,
            insight="Đỉnh nhưng ổn định — phù hợp làm hook thay thế ngay.",
        ),
    ]


def _fixture_cells_subniche() -> list[LifecycleCell]:
    """Six sub-niche cards for the subniche_breakdown mode."""
    return [
        LifecycleCell(
            name="Skincare routine",
            stage="rising",
            reach_delta_pct=34.0,
            health_score=84,
            instance_count=1240,
            insight="Ngách con dẫn đầu — routine sáng/tối + acid chain.",
        ),
        LifecycleCell(
            name="Ingredient deep-dive",
            stage="rising",
            reach_delta_pct=18.0,
            health_score=71,
            instance_count=680,
            insight="Cầu cao, cung thấp — cơ hội cho creator kiến thức.",
        ),
        LifecycleCell(
            name="Trước/sau 7 ngày",
            stage="rising",
            reach_delta_pct=22.0,
            health_score=76,
            instance_count=890,
            insight="Before/after vẫn đang chạy tốt — ưu tiên bằng chứng trực quan.",
        ),
        LifecycleCell(
            name="Product review solo",
            stage="plateau",
            reach_delta_pct=5.0,
            health_score=54,
            instance_count=2100,
            insight="Đông creator nhất nhưng retention đã chững.",
        ),
        LifecycleCell(
            name="Duet review KOL",
            stage="declining",
            reach_delta_pct=-3.0,
            health_score=44,
            instance_count=320,
            insight="Duet giảm dần — audience mệt với format response.",
        ),
        LifecycleCell(
            name="Unboxing haul",
            stage="declining",
            reach_delta_pct=-12.0,
            health_score=33,
            instance_count=540,
            insight="Unboxing thuần mất sức — cần gộp với routine hoặc story.",
        ),
    ]


def _fixture_refresh_moves() -> list[RefreshMove]:
    """Three refresh prescriptions — shared across modes because the
    tactics (change hook / change pacing / change audio) apply the same
    way to a declining format, hook, or subniche."""
    return [
        RefreshMove(
            title="Đổi audio sang trending tuần này",
            detail=(
                "Sound cũ đã được hơn 4 nghìn creator dùng — đổi sang top-5 trending "
                "ngách để thuật toán đánh giá lại."
            ),
            effort="low",
        ),
        RefreshMove(
            title="Rút hook về ≤ 1.2 giây",
            detail=(
                "Creator thắng trong 4 tuần gần nhất đều rút hook còn một câu 5–7 từ "
                "trong 1.2s đầu. Thử cắt bỏ câu giới thiệu."
            ),
            effort="medium",
        ),
        RefreshMove(
            title="Nạp thêm visual evidence trong 3–8s",
            detail=(
                "Slide/frame có số liệu hoặc close-up sản phẩm tăng retention 12–18% "
                "ở các hook đang suy yếu."
            ),
            effort="medium",
        ),
    ]


def _fixture_actions(mode: LifecycleMode) -> list[ActionCardPayload]:
    if mode == "format":
        return [
            ActionCardPayload(
                icon="sparkles",
                title="Chuyển sang short-form tuần tới",
                sub="Dùng kịch bản short-form từ Xưởng Viết cho 3 video tiếp theo",
                cta="Mở Xưởng Viết",
                primary=True,
                route="/app/script",
                forecast={"expected_range": "+28% reach", "baseline": "1.0× ngách"},
            ),
            ActionCardPayload(
                icon="search",
                title="Xem creator đang thắng short-form",
                sub="Benchmark với 3 creator dẫn đầu tuần này",
                cta="Mở kênh tham chiếu",
                route="/app/kol",
                forecast={"expected_range": "—", "baseline": "—"},
            ),
        ]
    if mode == "hook_fatigue":
        return [
            ActionCardPayload(
                icon="sparkles",
                title="Viết hook thay thế",
                sub="Dùng 1 trong 2 hook đang lên làm template mới",
                cta="Mở Xưởng Viết",
                primary=True,
                route="/app/script",
                forecast={"expected_range": "+14%", "baseline": "−18%"},
            ),
            ActionCardPayload(
                icon="calendar",
                title="Theo dõi fatigue tuần tới",
                sub="Đặt nhắc xem hook có phục hồi hay không",
                cta="Theo dõi",
                route="/app/trends",
                forecast={"expected_range": "—", "baseline": "—"},
            ),
        ]
    # subniche
    return [
        ActionCardPayload(
            icon="sparkles",
            title="Tạo brief cho ngách con #1",
            sub="Viết brief sản xuất ngay trong ngách đang lên mạnh nhất",
            cta="Mở Xưởng Viết",
            primary=True,
            route="/app/script",
            forecast={"expected_range": "+34% reach", "baseline": "1.0× ngách"},
        ),
        ActionCardPayload(
            icon="calendar",
            title="Theo dõi ngách con rising",
            sub="Xem weekly report để bắt sớm ngách con tiếp theo",
            cta="Xem weekly",
            route="/app/trends",
            forecast={"expected_range": "—", "baseline": "—"},
        ),
    ]


def build_fixture_lifecycle_report(mode: LifecycleMode = "format") -> dict[str, Any]:
    """Fixture ``LifecyclePayload`` in one of three modes.

    Used by pytest (schema validation) + frontend dev harnesses (render
    preview). The live pipeline replaces the cells + narrative via
    ``build_lifecycle_report`` (follow-up commit).
    """
    cells: list[LifecycleCell]
    subject: str
    related: list[str]
    sample_size: int

    if mode == "format":
        cells = _fixture_cells_format()
        subject = (
            "Short-form đang lên mạnh trong ngách — long-form giảm, carousel chững — "
            "chuyển 70% content sang 15–30s trong 2 tuần tới."
        )
        related = [
            "Khi nào thì chuyển hẳn sang short-form?",
            "Short-form nào phù hợp cho kênh < 10K?",
            "Long-form có còn chạy ở ngách con nào không?",
        ]
        sample_size = 310
    elif mode == "hook_fatigue":
        cells = _fixture_cells_hook_fatigue()
        subject = (
            "Hook 'Mình vừa test ___' đã giảm 18% trong 4 tuần — fatigue rõ ràng. "
            "Có 2 hook cùng họ vẫn đang lên để thay thế ngay."
        )
        related = [
            "Hook nào sẽ là người thay thế tiếp theo?",
            "Có thể refresh hook này bằng cách đổi audio không?",
            "Kênh mình (< 10K) có nên đổi sớm không?",
        ]
        sample_size = 94
    else:
        cells = _fixture_cells_subniche()
        subject = (
            "3 ngách con đang lên (Skincare routine, Ingredient deep-dive, Trước/sau 7 ngày) — "
            "Unboxing haul và Duet review KOL đang giảm rõ rệt."
        )
        related = [
            "Ngách con nào phù hợp kênh < 10K?",
            "Ingredient deep-dive cần bao nhiêu video để lên?",
            "Có overlap giữa routine và trước/sau không?",
        ]
        sample_size = 310

    # Only include refresh moves when at least one cell is declining or
    # plateau — the Pydantic invariant enforces this at validation time.
    has_weak_cell = any(c.stage in ("declining", "plateau") for c in cells)

    payload = LifecyclePayload(
        confidence=ConfidenceStrip(
            sample_size=sample_size,
            window_days=30,
            niche_scope="Skincare & Làm Đẹp",
            freshness_hours=8,
            intent_confidence="high",
        ),
        mode=mode,
        subject_line=subject,
        cells=cells,
        refresh_moves=_fixture_refresh_moves() if has_weak_cell else [],
        actions=_fixture_actions(mode),
        sources=[
            SourceRow(kind="video", label="Corpus", count=sample_size, sub="Skincare · 30d"),
        ],
        related_questions=related,
    )
    return payload.model_dump()


ANSWER_FIXTURE_LIFECYCLE_FORMAT: dict[str, Any] = validate_and_store_report(
    "lifecycle", build_fixture_lifecycle_report("format"),
)
ANSWER_FIXTURE_LIFECYCLE_HOOK_FATIGUE: dict[str, Any] = validate_and_store_report(
    "lifecycle", build_fixture_lifecycle_report("hook_fatigue"),
)
ANSWER_FIXTURE_LIFECYCLE_SUBNICHE: dict[str, Any] = validate_and_store_report(
    "lifecycle", build_fixture_lifecycle_report("subniche"),
)


# ── Live pipeline (stub — returns fixture until commit 3c lands) ────────────


def build_lifecycle_report(
    niche_id: int,  # noqa: ARG001 — wired in commit 3c
    query: str,  # noqa: ARG001 — wired in commit 3c
    mode: LifecycleMode = "format",
    window_days: int = 30,  # noqa: ARG001 — wired in commit 3c
) -> dict[str, Any]:
    """Live lifecycle report. STUB — returns the fixture until the
    live-aggregate + Gemini narrative code lands on this branch.

    Signature is final so commit 3c only has to replace the body; the
    intent-routing dispatch work in commit 3b can import this helper
    safely.
    """
    logger.info(
        "[lifecycle] fixture stub mode=%s niche=%s (live pipeline pending)",
        mode, niche_id,
    )
    return build_fixture_lifecycle_report(mode)
