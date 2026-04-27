"""D5b (2026-06-05) — Kho Douyin · weekly pattern signals synth.

Per design pack ``screens/douyin.jsx`` § I — "3 cards / niche / week".
Given one niche's last-7d Douyin corpus, this module asks Gemini to
cluster the videos into 3 named patterns, each with a fill-in-the-blank
hook template + a one-sentence format signature.

Inputs come from the orchestrator (D5c) which queries
``douyin_video_corpus`` rows for the niche, indexed within the last 7
days, ordered by views DESC, capped at the configured pool size:

  • title_zh / title_vi (D2a translator filled title_vi)
  • hook_type / hook_phrase (Gemini analysis from D2c)
  • content_format
  • views, cn_rise_pct (signal strength inputs)

Output (per migration ``20260605000000_douyin_patterns.sql``):

  • exactly 3 ``DouyinPattern`` rows, ranked 1-2-3 by signal strength
  • each row carries:
      ``rank`` ∈ {1, 2, 3}
      ``name_vn``           — pattern title in Vietnamese
      ``name_zh``           — closest Chinese phrasing (optional)
      ``hook_template_vi``  — fill-in-the-blank, e.g. "3 việc trước khi ___"
      ``format_signal_vi``  — one-sentence format/edit signature
      ``sample_video_ids``  — 2-5 anchor video_ids from the input pool

This module is the SYNTH side. D5c ships:

  • ``run_douyin_patterns_batch`` orchestrator (loops over the 10
    active niches, persists each batch with one upsert per row).
  • ``/batch/douyin-patterns`` HTTP endpoint.
  • Weekly pg_cron schedule (Mondays 04:00 VN).

Cost envelope (flash-preview at ~$0.25/M output tokens):

  Each call emits ~600 output tokens. 10 niches × 600 ≈ 6K tokens/week
  ≈ $0.0015/week — negligible compared to the daily D2 ingest cost.

Caching: ``_call_patterns_gemini`` is wrapped in lru_cache keyed on a
content-hash of the input pool. Re-runs within a week (manual trigger
or cron retry) skip the network if the pool is unchanged.
"""

from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


# ── Pydantic schema (enforced by Gemini's response_json_schema) ─────


PatternRank = Literal[1, 2, 3]


class DouyinPatternEntry(BaseModel):
    """One pattern card. The synthesiser emits exactly 3 of these per
    (niche, week)."""

    rank: PatternRank = Field(
        ...,
        description=(
            "1-based ordinal within the (niche, week) batch, ordered by "
            "signal strength (engagement, cn_rise_pct, sample size). 1 is "
            "the strongest, 3 is the weakest of the top 3."
        ),
    )
    name_vn: str = Field(
        ..., min_length=6, max_length=80,
        description=(
            "Pattern title in Vietnamese (≤ 80 chars). Concrete, not "
            "generic — e.g. 'Routine 3 bước trước khi ngủ' beats "
            "'Wellness routine'. No emoji, no trailing punctuation."
        ),
    )
    name_zh: str | None = Field(
        default=None, max_length=80,
        description=(
            "Closest Chinese phrasing for the pattern title (≤ 80 chars). "
            "Optional — when the pattern has no clean CN phrasing (e.g. "
            "format-only signature) leave it null."
        ),
    )
    hook_template_vi: str = Field(
        ..., min_length=8, max_length=120,
        description=(
            "Fill-in-the-blank Vietnamese hook template (≤ 120 chars). "
            "Use literal '___' for the blank. Example: "
            "'3 việc trước khi ___ — 1 tháng sau bạn sẽ khác'. "
            "Must contain at least one '___'."
        ),
    )
    format_signal_vi: str = Field(
        ..., min_length=20, max_length=240,
        description=(
            "One Vietnamese sentence describing the editing / pacing / "
            "framing signature (≤ 240 chars). Specific: 'Quay POV, "
            "transition cắt nhanh sau mỗi 1.5s, voiceover nhỏ.' beats "
            "'video ngắn, nhịp nhanh.'"
        ),
    )
    sample_video_ids: list[str] = Field(
        ..., min_length=2, max_length=5,
        description=(
            "2-5 anchor video_ids from the INPUT pool that best embody "
            "the pattern. MUST be a subset of the provided video_ids — "
            "the orchestrator validates membership before persisting."
        ),
    )

    @model_validator(mode="after")
    def _check_hook_has_blank(self) -> DouyinPatternEntry:
        if "___" not in self.hook_template_vi:
            raise ValueError(
                "hook_template_vi must contain a literal '___' blank "
                f"(got {self.hook_template_vi!r})"
            )
        return self

    @model_validator(mode="after")
    def _check_unique_sample_ids(self) -> DouyinPatternEntry:
        if len(set(self.sample_video_ids)) != len(self.sample_video_ids):
            raise ValueError(
                f"sample_video_ids must be unique (got {self.sample_video_ids!r})"
            )
        return self


class DouyinPatternsSynth(BaseModel):
    """Gemini-emitted pattern batch for one (niche, week). Always
    exactly 3 entries."""

    patterns: list[DouyinPatternEntry] = Field(
        ..., min_length=3, max_length=3,
        description=(
            "Exactly 3 pattern entries, ranked 1-2-3 by signal strength. "
            "Patterns must be DISTINCT — no two cards covering the same "
            "hook + format combination."
        ),
    )

    @model_validator(mode="after")
    def _check_ranks_are_unique_1_2_3(self) -> DouyinPatternsSynth:
        ranks = sorted(p.rank for p in self.patterns)
        if ranks != [1, 2, 3]:
            raise ValueError(
                f"patterns must use ranks {{1, 2, 3}} exactly once each, got {ranks}"
            )
        return self


# ── Public API ──────────────────────────────────────────────────────


class DouyinPatternsSynthInputVideo(BaseModel):
    """One input row for the synthesiser. Mirrors the columns the D5c
    orchestrator selects from ``douyin_video_corpus``."""

    video_id: str
    title_zh: str | None = None
    title_vi: str | None = None
    hook_phrase: str | None = None
    hook_type: str | None = None
    content_format: str | None = None
    views: int = 0
    cn_rise_pct: float | None = None


# Minimum corpus size to even attempt synthesis. Below this the
# synthesiser cannot reliably cluster — orchestrator returns None and
# skips writing the (niche, week) batch.
MIN_INPUT_POOL = 6


def synth_douyin_patterns(
    *,
    niche_name_vn: str,
    niche_name_zh: str,
    videos: list[DouyinPatternsSynthInputVideo],
) -> DouyinPatternsSynth | None:
    """Cluster a niche's last-7d corpus into 3 named patterns.

    Returns ``None`` on:

      • input pool below ``MIN_INPUT_POOL`` (orchestrator skips niche).
      • Gemini / Pydantic-validation failure (orchestrator re-tries on
        the next cron run).
      • any returned ``sample_video_ids`` falling outside the input pool
        (Gemini hallucination guard).
    """
    if len(videos) < MIN_INPUT_POOL:
        logger.info(
            "[douyin-patterns] niche=%s pool=%d below MIN_INPUT_POOL=%d — skipping",
            niche_name_vn, len(videos), MIN_INPUT_POOL,
        )
        return None

    pool_ids: set[str] = {v.video_id for v in videos}
    fingerprint = _content_fingerprint(videos)
    try:
        result = _call_patterns_gemini(
            niche_name_vn=niche_name_vn.strip(),
            niche_name_zh=niche_name_zh.strip(),
            videos_json=_serialise_videos(videos),
            fingerprint=fingerprint,
        )
    except Exception as exc:
        logger.warning(
            "[douyin-patterns] failed for niche=%s pool=%d: %s",
            niche_name_vn, len(videos), exc,
        )
        return None

    # Hallucination guard — every sample_video_id must be in the input
    # pool. If Gemini fabricated one (rare with response_json_schema
    # but possible), the orchestrator re-attempts next run.
    for entry in result.patterns:
        bad = [vid for vid in entry.sample_video_ids if vid not in pool_ids]
        if bad:
            logger.warning(
                "[douyin-patterns] niche=%s rank=%d returned out-of-pool "
                "sample_video_ids=%r — discarding batch",
                niche_name_vn, entry.rank, bad,
            )
            return None

    return result


# ── Internals ───────────────────────────────────────────────────────


def _serialise_videos(videos: list[DouyinPatternsSynthInputVideo]) -> str:
    """Compact JSON for the prompt — short keys keep the input token
    cost down, and lru_cache only sees the hashable string."""
    rows = []
    for v in videos:
        rows.append({
            "id": v.video_id,
            "zh": (v.title_zh or "")[:140],
            "vi": (v.title_vi or "")[:140],
            "hook": (v.hook_phrase or "")[:80],
            "hook_type": v.hook_type or "",
            "format": v.content_format or "",
            "views": int(v.views),
            "rise": v.cn_rise_pct,
        })
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def _content_fingerprint(videos: list[DouyinPatternsSynthInputVideo]) -> str:
    """Stable digest over the input pool so lru_cache hits across same-
    week re-runs. Uses video_id + title + views — anything that would
    change the synthesis output."""
    parts = []
    for v in sorted(videos, key=lambda x: x.video_id):
        parts.append(
            f"{v.video_id}|{v.title_zh or ''}|{v.title_vi or ''}|"
            f"{v.views}|{v.cn_rise_pct}"
        )
    h = hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
    return h[:16]


@lru_cache(maxsize=64)
def _call_patterns_gemini(
    *,
    niche_name_vn: str,
    niche_name_zh: str,
    videos_json: str,
    fingerprint: str,  # noqa: ARG001 — lru_cache key only
) -> DouyinPatternsSynth:
    """Pydantic-bound Gemini call. Raises on any failure — caller
    catches.

    The ``fingerprint`` arg is a content-hash of the input pool so
    lru_cache actually sees a stable key across re-runs of the same
    week. ``videos_json`` is the prompt content; both are kwargs so
    test-only patches at ``_generate_content_models`` exercise the
    cache rather than bypassing it (mirrors the D2a/D3a pattern).
    """
    from google.genai import types  # type: ignore[import-untyped]

    from getviews_pipeline.config import (
        GEMINI_SYNTHESIS_FALLBACKS,
        GEMINI_SYNTHESIS_MODEL,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    prompt = f"""Bạn là editor TikTok Việt Nam phân tích corpus Douyin tuần này để tổng hợp 3 PATTERN viral mạnh nhất trong ngách.

NGÁCH: {niche_name_vn} ({niche_name_zh})

CORPUS (JSON, video_id → metadata):
{videos_json}

NHIỆM VỤ — trả về JSON với key ``patterns`` chứa CHÍNH XÁC 3 entry:

Mỗi entry mô tả 1 PATTERN xuất hiện ≥ 2 lần trong corpus. Pattern = sự kết hợp đặc trưng của hook + format + bối cảnh. Ví dụ:
  - "3 việc trước khi ___ — 1 tháng sau bạn sẽ khác" + POV unboxing chậm + voiceover thì thầm = 1 pattern.
  - "Tôi đã thử ___ trong 30 ngày" + before/after split-screen + nhạc upbeat = 1 pattern khác.

Cho mỗi entry:

1. ``rank`` (1, 2, hoặc 3) — 1 là pattern signal mạnh nhất (xuất hiện nhiều, view cao, rise dương). Mỗi rank dùng đúng 1 lần.

2. ``name_vn`` (≤ 80 ký tự) — tên pattern bằng tiếng Việt, cụ thể không chung chung. KHÔNG emoji, KHÔNG dấu câu cuối câu.

3. ``name_zh`` (optional) — phrasing tiếng Trung gần nhất (≤ 80 ký tự). Nếu pattern là format-only (không có hook đặc trưng CN) → null.

4. ``hook_template_vi`` (≤ 120 ký tự) — hook fill-in-the-blank, dùng literal "___" cho chỗ trống. BẮT BUỘC phải có ít nhất 1 chuỗi "___".

5. ``format_signal_vi`` (≤ 240 ký tự) — 1 câu mô tả editing / nhịp / khung hình. Cụ thể: "Quay POV, transition cắt nhanh sau mỗi 1.5s, voiceover nhỏ" tốt hơn "video ngắn nhịp nhanh".

6. ``sample_video_ids`` (2-5 entry) — danh sách video_id từ CORPUS làm anchor cho pattern. BẮT BUỘC nằm trong corpus đầu vào — không tự bịa id.

QUY TẮC COPY:
- Tự nhiên, đời thường tiếng Việt. Tránh "bí mật", "công thức vàng", "triệu view", "bùng nổ", "đột phá".
- Không mở "Đây là", "Pattern này".
- 3 pattern PHẢI khác biệt — không 2 card cùng hook + format.
- Nếu corpus quá đồng nhất để tách 3 pattern khác biệt, vẫn cố tách theo bối cảnh / props / nhịp khác nhau.
"""

    config = types.GenerateContentConfig(
        temperature=0.4,
        response_mime_type="application/json",
        response_json_schema=DouyinPatternsSynth.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return DouyinPatternsSynth.model_validate_json(_normalize_response(raw))


# ── Test-only hook (lets pytest reset the lru_cache) ────────────────


def _reset_cache_for_tests() -> None:
    _call_patterns_gemini.cache_clear()
