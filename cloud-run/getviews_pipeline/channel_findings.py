"""Channel diagnosis findings layer (§5.3.3 P0) — evidence-backed memo inject."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from getviews_pipeline.channel_diagnose import classify_format

Strength = Literal["low", "medium", "high"]
PROMPT_FINDINGS_CAP = 8

_FORMAT_ENTROPY_HIGH = 2.2
_PEER_FORMAT_SATURATION_PCT = 70


def format_distribution_from_corpus_rows(
    rows: list[dict[str, Any]] | None,
) -> dict[str, int]:
    """Share % by ``content_format`` from peer corpus rows (§5.3.5)."""
    if not rows:
        return {}
    counter: Counter[str] = Counter()
    for row in rows:
        fmt = str(row.get("content_format") or "").strip()
        if fmt:
            counter[fmt] += 1
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {fmt: round(100 * n / total) for fmt, n in counter.items()}


def _cohort_er_threshold_pct(niche_benchmarks: dict[str, Any] | None) -> float:
    """Low-ER bar for view-ceiling finding — p50×0.85 proxy when p25 absent."""
    default = 2.0
    if not niche_benchmarks:
        return default
    for key, scale in (("engagement_p25", 1.0), ("engagement_p50", 0.85)):
        raw = niche_benchmarks.get(key)
        if raw is None:
            continue
        try:
            v = float(raw) * scale
            return v * 100.0 if v <= 1.0 else v
        except (TypeError, ValueError):
            continue
    return default


@dataclass(frozen=True)
class ChannelFinding:
    id: str
    taxonomy_ref: str
    strength: Strength
    claim: str
    evidence: list[str]
    section_hint: str
    salience: float


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _video_er_pct(video: dict[str, Any]) -> float:
    views = int(video.get("views") or 0)
    if views <= 0:
        return 0.0
    likes = int(video.get("likes") or 0)
    comments = int(video.get("comments") or 0)
    return (likes + comments) / views * 100.0


def _shannon_entropy(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def _finding_view_ceiling_300(
    videos: list[dict[str, Any]],
    *,
    er_threshold_pct: float,
) -> ChannelFinding | None:
    cutoff = _now() - timedelta(days=90)
    low_ceiling: list[dict[str, Any]] = []
    for v in videos:
        posted = v.get("posted_at")
        if posted and isinstance(posted, datetime) and posted < cutoff:
            continue
        views = int(v.get("views") or 0)
        if views > 300:
            continue
        er = _video_er_pct(v)
        if er >= er_threshold_pct:
            continue
        low_ceiling.append(v)

    if len(low_ceiling) < 3:
        return None

    n = len(low_ceiling)
    return ChannelFinding(
        id="channel_view_ceiling_300",
        taxonomy_ref="§2.1",
        strength="high" if n >= 5 else "medium",
        claim=(
            f"{n} video gần đây kẹt dưới ~300 view với ER thấp — "
            "có dấu hiệu trần phân phối tài khoản; GetViews không đọc được FYP %."
        ),
        evidence=[
            f"low_view_low_er_count={n}/90d",
            f"er_threshold_pct={er_threshold_pct:.1f}",
        ],
        section_hint="verdict",
        salience=0.92 if n >= 5 else 0.85,
    )


def _finding_format_entropy_high(
    videos: list[dict[str, Any]],
    *,
    niche_format_distribution: dict[str, Any] | None,
) -> ChannelFinding | None:
    if len(videos) < 5:
        return None

    fmt_counts: dict[str, int] = {}
    for v in videos:
        fmt = str(v.get("content_format") or classify_format(v))
        fmt_counts[fmt] = fmt_counts.get(fmt, 0) + 1

    entropy = _shannon_entropy(fmt_counts)
    if entropy < _FORMAT_ENTROPY_HIGH:
        return None

    top_fmt, top_n = max(fmt_counts.items(), key=lambda kv: kv[1])
    top_share = round(100 * top_n / len(videos))

    niche_note = ""
    if isinstance(niche_format_distribution, dict) and niche_format_distribution:
        niche_top = max(niche_format_distribution.items(), key=lambda kv: int(kv[1] or 0))
        niche_note = f"niche_top_format={niche_top[0]}({niche_top[1]}%)"

    return ChannelFinding(
        id="channel_format_entropy_high",
        taxonomy_ref="§2.2",
        strength="medium",
        claim=(
            f"Format kênh phân tán (entropy={entropy:.2f}) — top chỉ {top_share}% "
            f"({top_fmt}); có dấu hiệu thiếu nhất quán ngách so với peer."
        ),
        evidence=[
            f"format_entropy={entropy:.2f}",
            f"top_format_share={top_share}%",
            niche_note or "niche_format_distribution=unavailable",
        ],
        section_hint="what_falling",
        salience=0.78,
    )


def _finding_recent_vs_peak_er_drop(
    videos: list[dict[str, Any]],
    recent_window_30d: dict[str, Any],
    inflection: dict[str, Any] | None,
    channel_pattern: dict[str, Any],
) -> ChannelFinding | None:
    recent_count = int(recent_window_30d.get("video_count") or 0)
    if recent_count < 2:
        return None

    cutoff = _now() - timedelta(days=30)
    recent_vids = [
        v for v in videos
        if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    if not recent_vids:
        return None

    recent_er = sum(_video_er_pct(v) for v in recent_vids) / len(recent_vids)
    recent_avg = int(recent_window_30d.get("avg_views") or 0)

    peak_avg = int(channel_pattern.get("max_views") or 0)
    peak_er = recent_er
    if inflection:
        peak_avg = int(inflection.get("peak_avg") or peak_avg)
        peak_q = str(inflection.get("peak_quarter") or "")
        peak_start = inflection.get("peak_quarter_start")
        if peak_start and isinstance(peak_start, datetime):
            peak_vids = [
                v for v in videos
                if v.get("posted_at") and v["posted_at"] >= peak_start
            ]
            if peak_vids:
                peak_er = sum(_video_er_pct(v) for v in peak_vids) / len(peak_vids)
        elif peak_q:
            peak_vids = [v for v in videos if peak_q in str(v.get("posted_at") or "")]
            if peak_vids:
                peak_er = sum(_video_er_pct(v) for v in peak_vids) / len(peak_vids)

    if peak_avg <= 0 or recent_avg <= 0:
        return None

    view_drop_pct = (1.0 - recent_avg / peak_avg) * 100.0 if peak_avg > recent_avg else 0.0
    er_drop = peak_er - recent_er
    if view_drop_pct < 25.0 and er_drop < 1.0:
        return None

    return ChannelFinding(
        id="channel_recent_vs_peak_er_drop",
        taxonomy_ref="§2.2",
        strength="high" if view_drop_pct >= 40 else "medium",
        claim=(
            f"30 ngày gần: avg {recent_avg} view, ER ~{recent_er:.1f}% — "
            f"so đỉnh {peak_avg} view / ER ~{peak_er:.1f}%: có dấu hiệu lệch audience hoặc mất nhịp."
        ),
        evidence=[
            f"recent_30d_avg_views={recent_avg}",
            f"recent_er_pct={recent_er:.2f}",
            f"peak_avg_views={peak_avg}",
            f"peak_er_pct={peak_er:.2f}",
            f"view_drop_pct={view_drop_pct:.1f}",
        ],
        section_hint="what_falling",
        salience=0.88 if view_drop_pct >= 40 else 0.80,
    )


def _finding_peer_format_saturation(
    peer_corpus_rows: list[dict[str, Any]] | None,
    *,
    dominant_format: str | None,
) -> ChannelFinding | None:
    if not peer_corpus_rows or not dominant_format:
        return None

    fmt = str(dominant_format).strip()
    if not fmt:
        return None

    cutoff = _now() - timedelta(days=7)
    recent_peers: list[dict[str, Any]] = []
    for row in peer_corpus_rows[:20]:
        indexed = row.get("indexed_at")
        if indexed:
            if isinstance(indexed, str):
                try:
                    indexed_dt = datetime.fromisoformat(indexed.replace("Z", "+00:00"))
                except ValueError:
                    indexed_dt = None
            elif isinstance(indexed, datetime):
                indexed_dt = indexed if indexed.tzinfo else indexed.replace(tzinfo=UTC)
            else:
                indexed_dt = None
            if indexed_dt and indexed_dt < cutoff:
                continue
        recent_peers.append(row)

    pool = recent_peers if recent_peers else peer_corpus_rows[:20]
    if len(pool) < 5:
        return None

    same_fmt = sum(
        1 for r in pool
        if str(r.get("content_format") or "").strip() == fmt
    )
    share_pct = round(100 * same_fmt / len(pool))
    if share_pct < _PEER_FORMAT_SATURATION_PCT:
        return None

    return ChannelFinding(
        id="channel_peer_format_saturation",
        taxonomy_ref="§2.3",
        strength="medium",
        claim=(
            f"{share_pct}% video corpus top ngách 7d cùng format `{fmt}` — "
            "có dấu hiệu bão hòa format; cần góc lệch rõ so peer."
        ),
        evidence=[
            f"peer_format={fmt}",
            f"peer_same_format_share={share_pct}%",
            f"peer_sample_n={len(pool)}",
        ],
        section_hint="competitive_landscape",
        salience=0.76,
    )


def build_channel_findings(
    *,
    videos: list[dict[str, Any]],
    channel_pattern: dict[str, Any],
    recent_window_30d: dict[str, Any],
    inflection: dict[str, Any] | None,
    niche_benchmarks: dict[str, Any] | None = None,
    peer_corpus_rows: list[dict[str, Any]] | None = None,
    dominant_format: str | None = None,
    niche_format_distribution: dict[str, Any] | None = None,
) -> list[ChannelFinding]:
    """Return P0 findings sorted by salience desc (prompt caps at top 8)."""
    er_threshold = _cohort_er_threshold_pct(niche_benchmarks)

    candidates: list[ChannelFinding] = []
    for builder in (
        lambda: _finding_view_ceiling_300(videos, er_threshold_pct=er_threshold),
        lambda: _finding_format_entropy_high(
            videos, niche_format_distribution=niche_format_distribution,
        ),
        lambda: _finding_recent_vs_peak_er_drop(
            videos, recent_window_30d, inflection, channel_pattern,
        ),
        lambda: _finding_peer_format_saturation(
            peer_corpus_rows, dominant_format=dominant_format,
        ),
    ):
        finding = builder()
        if finding:
            candidates.append(finding)

    candidates.sort(key=lambda f: -f.salience)
    return candidates


def format_findings_for_prompt(findings: list[ChannelFinding]) -> str:
    """Render top findings for LLM context block."""
    if not findings:
        return ""
    lines = ["<<<CHANNEL FINDINGS>>>"]
    for f in findings[:PROMPT_FINDINGS_CAP]:
        ev = "; ".join(f.evidence)
        lines.append(
            f"- id={f.id} | strength={f.strength} | section_hint={f.section_hint} | "
            f"claim={f.claim} | evidence={ev}"
        )
    lines.append(
        "(Dùng findings làm bằng chứng số — KHÔNG khẳng định FYP % hay shadowban chắc chắn.)"
    )
    return "\n".join(lines)
