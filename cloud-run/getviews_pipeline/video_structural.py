"""Deterministic structural helpers for Phase B /video (timeline + hook slots).

LLM fills bounded copy elsewhere; this module stays pure JSON in → JSON out.
"""

from __future__ import annotations

import math
from typing import Any, Final

# Reference layout: `artifacts/uiux-reference/screens/video.jsx` Timeline().
# Percentages sum to 100; used when scenes are missing or unusable.
_FALLBACK_SEGMENT_PCTS: Final[tuple[tuple[str, int, str], ...]] = (
    ("HOOK", 5, "accent"),
    ("PROMISE", 8, "ink-2"),
    ("APP 1", 14, "ink-3"),
    ("APP 2", 14, "ink-2"),
    ("APP 3", 14, "ink-3"),
    ("APP 4", 14, "ink-2"),
    ("APP 5", 16, "ink-3"),
    ("CTA", 15, "accent-deep"),
)


def _floatish(x: Any, default: float = 0.0) -> float:
    if x is None:
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def video_duration_sec(analysis: dict[str, Any]) -> float:
    """Total seconds for timeline — prefer explicit field, else last scene end."""
    raw = analysis.get("duration_seconds")
    if raw is not None and str(raw).strip() != "":
        d = _floatish(raw, 0.0)
        if d > 0:
            return d
    scenes = analysis.get("scenes") or []
    if not isinstance(scenes, list) or not scenes:
        return 0.0
    ends: list[float] = []
    for sc in scenes:
        if isinstance(sc, dict):
            ends.append(_floatish(sc.get("end"), 0.0))
    return max(ends) if ends else 0.0


def decompose_segments(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Map `scenes[]` timestamps into eight named segments with integer pcts summing to 100.

    Each item: ``{"name": str, "pct": int, "color_key": str}`` — ``color_key`` is a
    token key for the SPA (maps to ``var(--gv-*)`` in components).
    """
    duration = video_duration_sec(analysis)
    scenes_raw = analysis.get("scenes") or []
    if not isinstance(scenes_raw, list) or not scenes_raw or duration <= 0:
        return [{"name": n, "pct": p, "color_key": c} for n, p, c in _FALLBACK_SEGMENT_PCTS]

    intervals: list[tuple[float, float]] = []
    for sc in scenes_raw:
        if not isinstance(sc, dict):
            continue
        start = max(0.0, _floatish(sc.get("start"), 0.0))
        end = max(start, _floatish(sc.get("end"), start))
        end = min(end, duration)
        if end - start <= 1e-6:
            continue
        intervals.append((start, end))
    if not intervals:
        return [{"name": n, "pct": p, "color_key": c} for n, p, c in _FALLBACK_SEGMENT_PCTS]

    intervals.sort(key=lambda x: x[0])
    merged: list[tuple[float, float]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1e-6:
            merged.append((start, end))
        else:
            prev_s, prev_e = merged[-1]
            merged[-1] = (prev_s, max(prev_e, end))

    # Merge down to at most 8 contiguous spans (combine smallest adjacent pair).
    while len(merged) > 8:
        best_i = 0
        best_w = float("inf")
        for i in range(len(merged) - 1):
            w = merged[i + 1][1] - merged[i][0]
            if w < best_w:
                best_w = w
                best_i = i
        a_s, _ = merged[best_i]
        _, b_e = merged[best_i + 1]
        merged = merged[:best_i] + [(a_s, b_e)] + merged[best_i + 2 :]

    # Split up to reach exactly 8 spans (longest piece first).
    def span_len(t: tuple[float, float]) -> float:
        return t[1] - t[0]

    working = list(merged)
    while len(working) < 8:
        idx = max(range(len(working)), key=lambda i: span_len(working[i]))
        s, e = working[idx]
        if e - s < 0.2:  # avoid infinite split on tiny slivers
            break
        mid = (s + e) / 2.0
        working = working[:idx] + [(s, mid), (mid, e)] + working[idx + 1 :]

    if len(working) != 8:
        return [{"name": n, "pct": p, "color_key": c} for n, p, c in _FALLBACK_SEGMENT_PCTS]

    names = [t[0] for t in _FALLBACK_SEGMENT_PCTS]
    colors = [t[2] for t in _FALLBACK_SEGMENT_PCTS]
    total_span = sum(span_len(t) for t in working) or 1.0
    raw_pcts = [100.0 * span_len(t) / total_span for t in working]

    # Integer pcts summing to 100
    floors = [int(math.floor(p)) for p in raw_pcts]
    remainder = 100 - sum(floors)
    frac = sorted(
        enumerate([rp - math.floor(rp) for rp in raw_pcts]),
        key=lambda x: x[1],
        reverse=True,
    )
    for j in range(remainder):
        floors[frac[j % len(floors)][0]] += 1

    out: list[dict[str, Any]] = []
    for i, pct in enumerate(floors):
        name = names[i] if i < len(names) else f"SEG {i + 1}"
        ck = colors[i] if i < len(colors) else "ink-3"
        out.append({"name": name, "pct": pct, "color_key": ck})
    return out


def extract_hook_phases(analysis: dict[str, Any]) -> list[dict[str, str]]:
    """Three hook window cards: deterministic ``t_range`` + ``label``; ``body`` is LLM-only (empty here).

    All enum values (``first_frame_type``, hook-timeline ``event``) are routed
    through ``enum_labels_vi`` before concatenation so the QA audit's BUG-02
    regression ("Mở face with text · face @0.0s", "face_enter: Speaker's face
    is visible.") cannot recur. The original raw values stay in ``hook_type``
    / metadata for admin/debug surfaces — only the user-visible ``label``
    gets translated.
    """
    from getviews_pipeline.enum_labels_vi import (
        first_frame_vi,
        hook_timeline_event_vi,
        hook_type_vi,
    )

    ha = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else {}
    first_frame = str(ha.get("first_frame_type") or "other")
    hook_type = str(ha.get("hook_type") or "other")
    face_at = ha.get("face_appears_at")
    speech_at = ha.get("first_speech_at")
    face_s: float | None = None
    if face_at is not None and str(face_at).strip() != "":
        face_s = _floatish(face_at)
    speech_s: float | None = None
    if speech_at is not None and str(speech_at).strip() != "":
        speech_s = _floatish(speech_at)

    label_a = f"Mở: {first_frame_vi(first_frame, default='Khác')}"
    if face_s is not None:
        label_a = f"{label_a} · mặt lên @{face_s:.1f}s"

    label_b = f"Kiểu hook: {hook_type_vi(hook_type, default='Khác')}"
    timeline = ha.get("hook_timeline") or []
    if isinstance(timeline, list) and timeline:
        first_ev = timeline[0] if isinstance(timeline[0], dict) else {}
        ev_raw = str(first_ev.get("event") or "")
        note = str(first_ev.get("note") or "").strip()
        ev_vi = hook_timeline_event_vi(ev_raw, default="")
        if ev_vi or note:
            label_b = f"{ev_vi}{(': ' + note) if note else ''}".strip(" :")

    label_c = "Cam kết / payoff trong 3s đầu"
    if speech_s is not None:
        label_c = f"Lời đầu @{speech_s:.1f}s"

    return [
        {"t_range": "0.0–0.8s", "label": label_a[:120], "body": ""},
        {"t_range": "0.8–1.8s", "label": label_b[:120], "body": ""},
        {"t_range": "1.8–3.0s", "label": label_c[:120], "body": ""},
    ]


def model_retention_curve(
    duration_sec: float,
    *,
    niche_median_retention: float | None = None,
    breakout_multiplier: float | None = None,
    n_points: int = 20,
) -> list[dict[str, float]]:
    """Modeled retention curve (Phase B default until real telemetry exists).

    ``niche_median_retention``: 0–1 fraction at t ≈ duration (e.g. 0.58).
    ``breakout_multiplier``: optional >1 flattens early drop-off slightly.
    """
    dur = max(float(duration_sec), 0.1)
    end_pct = 100.0 * float(niche_median_retention or 0.45)
    end_pct = min(max(end_pct, 5.0), 95.0)
    boost = float(breakout_multiplier or 1.0)
    boost = min(max(boost, 1.0), 5.0)
    # Higher breakout → retain more in the middle (simple heuristic).
    mid_lift = 1.0 + 0.08 * math.log(boost)

    out: list[dict[str, float]] = []
    for i in range(n_points):
        t = dur * i / max(n_points - 1, 1)
        u = i / max(n_points - 1, 1)
        # Smooth decay from 100 toward end_pct, with slight "lift" in the middle.
        base = 100.0 * (1.0 - u) + end_pct * u
        bump = mid_lift * 8.0 * u * (1.0 - u)
        pct = min(100.0, max(0.0, base + bump - 4.0 * u))
        out.append({"t": round(t, 3), "pct": round(pct, 2)})
    return out


def model_niche_benchmark_curve(
    duration_sec: float,
    *,
    niche_median_retention: float | None = None,
    n_points: int = 20,
) -> list[dict[str, float]]:
    """A slightly flatter dashed "niche" curve for the same duration (UI overlay)."""
    inner = niche_median_retention
    if inner is None:
        inner = 0.5
    else:
        inner = min(max(float(inner) + 0.08, 0.1), 0.92)
    return model_retention_curve(
        duration_sec,
        niche_median_retention=inner,
        breakout_multiplier=1.0,
        n_points=n_points,
    )
