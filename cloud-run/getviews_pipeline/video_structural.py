"""Deterministic structural helpers for Phase B /video (timeline + hook slots).

LLM fills bounded copy elsewhere; this module stays pure JSON in → JSON out.
"""

from __future__ import annotations

import math
import re
from typing import Any, Final

# Reference layout: `artifacts/uiux-reference/screens/video.jsx` Timeline().
# Percentages sum to 100; used when scenes are missing or unusable.
# Hook decode strip — three cards, half-open partition of 0–3s (v4 HOOK-TS).
HOOK_PHASE_WINDOWS: Final[tuple[tuple[float, float], ...]] = (
    (0.0, 0.8),
    (0.8, 1.8),
    (1.8, 3.0),
)


def _hook_phase_slot(ts: float | None) -> int | None:
    """Return card index 0..2 for timestamps in the hook window; None if outside 0–3s."""
    if ts is None:
        return None
    try:
        t = float(ts)
    except (TypeError, ValueError):
        return None
    if t < 0.0 or t > 3.0:
        return None
    if t < 0.8:
        return 0
    if t < 1.8:
        return 1
    return 2


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

    # Short clips: 8 near-equal beats = no real structure (audit TIMELINE-NOISE v4).
    # Longer clips may still look equal after the 8-bucket merge — FE hides those bars.
    if duration <= 20.0 and len(floors) >= 8 and max(floors) - min(floors) < 5:
        return []

    scene_out: list[dict[str, Any]] = []
    for i, pct in enumerate(floors):
        name = names[i] if i < len(names) else f"SEG {i + 1}"
        ck = colors[i] if i < len(colors) else "ink-3"
        s_start, s_end = working[i]
        scene_out.append(
            {
                "name": name,
                "pct": pct,
                "color_key": ck,
                "start_sec": round(s_start, 2),
                "end_sec": round(s_end, 2),
            }
        )
    return scene_out


def extract_hook_phases(analysis: dict[str, Any]) -> list[dict[str, str]]:
    """Three hook window cards: fixed ``t_range`` + assembled ``label``; ``body`` is empty.

    All enum values (``first_frame_type``, hook-timeline ``event``) are routed
    through ``enum_labels_vi`` before concatenation so the QA audit's BUG-02
    regression ("Mở face with text · face @0.0s", "face_enter: Speaker's face
    is visible.") cannot recur. The original raw values stay in ``hook_type``
    / metadata for admin/debug surfaces — only the user-visible ``label``
    gets translated.
    """
    from getviews_pipeline.analysis_guards import strip_out_of_range_timestamps
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

    parts: list[list[str]] = [[], [], []]
    parts[0].append(f"Mở: {first_frame_vi(first_frame, default='Khác')}")
    parts[1].append(f"Kiểu hook: {hook_type_vi(hook_type, default='Khác')}")
    parts[2].append("Cam kết / payoff trong 3s đầu")

    if face_s is not None:
        fi = _hook_phase_slot(face_s)
        if fi is not None:
            parts[fi].append(f"mặt lên @{face_s:.1f}s")

    if speech_s is not None:
        si = _hook_phase_slot(speech_s)
        if si is not None:
            if si == 2:
                parts[2] = [x for x in parts[2] if x != "Cam kết / payoff trong 3s đầu"]
            parts[si].append(f"Lời đầu @{speech_s:.1f}s")

    timeline = ha.get("hook_timeline") or []
    if isinstance(timeline, list):
        for ev in timeline:
            if not isinstance(ev, dict):
                continue
            t_ev = ev.get("t")
            if t_ev is None:
                continue
            wi = _hook_phase_slot(_floatish(t_ev))
            if wi is None:
                continue
            ev_raw = str(ev.get("event") or "")
            note = str(ev.get("note") or "").strip()
            ev_vi = hook_timeline_event_vi(ev_raw, default="")
            lo, hi = HOOK_PHASE_WINDOWS[wi]
            note = strip_out_of_range_timestamps(note, lo, hi)
            line = f"{ev_vi}{(': ' + note) if note else ''}".strip(" :")
            if line:
                parts[wi].append(line)

    cards: list[dict[str, str]] = []
    for i, (lo, hi) in enumerate(HOOK_PHASE_WINDOWS):
        label = " · ".join(s for s in parts[i] if s).strip()
        label = strip_out_of_range_timestamps(label, lo, hi)
        label = re.sub(r"\s*·\s*·+\s*", " · ", label)
        label = re.sub(r"\s{2,}", " ", label).strip(" ·")
        if i == 2 and not label:
            label = "Cam kết / payoff trong 3s đầu"
        cards.append({"t_range": f"{lo:.1f}–{hi:.1f}s", "label": label[:120], "body": ""})

    return cards


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


# ── Structure-driven retention (v1) ─────────────────────────────────────

DEAD_AIR_GAP_SEC: Final[float] = 1.2
STATIC_SCENE_NORM_SEC: Final[float] = 4.0
OPENING_WINDOW_SEC: Final[float] = 3.0
_PATTERN_INTERRUPT_EVENTS: Final[frozenset[str]] = frozenset(
    {"cut", "reveal", "product_enter", "sound_drop"}
)


def _format_mmss(seconds: float) -> str:
    sec = max(0.0, float(seconds))
    m = int(sec // 60)
    s = int(round(sec % 60))
    return f"{m}:{s:02d}"


def _retention_end_pct(
    niche_median_retention: float | None,
    breakout_multiplier: float | None,
) -> tuple[float, float]:
    end_pct = 100.0 * float(niche_median_retention or 0.45)
    end_pct = min(max(end_pct, 5.0), 95.0)
    boost = float(breakout_multiplier or 1.0)
    boost = min(max(boost, 1.0), 5.0)
    mid_lift = 1.0 + 0.08 * math.log(boost)
    return end_pct, mid_lift


def _asr_silence_gaps(
    segments: list[dict[str, Any]],
    *,
    duration_sec: float,
    min_gap: float = DEAD_AIR_GAP_SEC,
) -> list[tuple[float, float]]:
    ordered: list[tuple[float, float]] = []
    for seg in segments:
        try:
            st = float(seg.get("start_sec"))
            en = float(seg.get("end_sec"))
        except (TypeError, ValueError):
            continue
        if en > st:
            ordered.append((st, en))
    if not ordered:
        return []
    ordered.sort(key=lambda p: p[0])
    gaps: list[tuple[float, float]] = []
    prev_end = 0.0
    for st, en in ordered:
        if st - prev_end >= min_gap:
            gaps.append((prev_end, st))
        prev_end = max(prev_end, en)
    if duration_sec - prev_end >= min_gap:
        gaps.append((prev_end, duration_sec))
    return gaps


def _scene_gap_approximations(scenes: list[dict[str, Any]]) -> list[tuple[float, float]]:
    ordered: list[tuple[float, float]] = []
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        st = _floatish(sc.get("start"))
        en = _floatish(sc.get("end"))
        if en > st:
            ordered.append((st, en))
    if len(ordered) < 2:
        return []
    ordered.sort(key=lambda p: p[0])
    gaps: list[tuple[float, float]] = []
    for i in range(len(ordered) - 1):
        gap = ordered[i + 1][0] - ordered[i][1]
        if gap >= DEAD_AIR_GAP_SEC:
            gaps.append((ordered[i][1], ordered[i + 1][0]))
    return gaps


def _collect_structural_risks(
    duration_sec: float,
    scenes: list[dict[str, Any]],
    *,
    asr_segments: list[dict[str, Any]] | None,
    hook_timeline: list[dict[str, Any]] | None,
    hook_analysis: dict[str, Any] | None,
    audio_track_role: str | None,
) -> list[dict[str, Any]]:
    """Return weighted risk intervals with provenance for curve allocation."""
    dur = max(float(duration_sec), 0.1)
    risks: list[dict[str, Any]] = []
    role = str(audio_track_role or "").strip().lower()
    ha = hook_analysis if isinstance(hook_analysis, dict) else {}

    if asr_segments and role != "silent":
        for lo, hi in _asr_silence_gaps(asr_segments, duration_sec=dur):
            mid = (lo + hi) / 2.0
            gap = hi - lo
            risks.append(
                {
                    "start": lo,
                    "end": hi,
                    "t": mid,
                    "weight": 1.2 + gap * 0.35,
                    "severity": min(1.0, gap / 3.0),
                    "reason_vi": f"khoảng lặng ~{_format_mmss(mid)} ({gap:.1f}s)",
                    "source": "asr",
                }
            )
    elif role != "silent":
        for lo, hi in _scene_gap_approximations(scenes):
            mid = (lo + hi) / 2.0
            gap = hi - lo
            risks.append(
                {
                    "start": lo,
                    "end": hi,
                    "t": mid,
                    "weight": 0.8 + gap * 0.25,
                    "severity": min(0.85, gap / 3.5),
                    "reason_vi": (
                        f"khoảng chuyển cảnh ước tính {_format_mmss(lo)}–{_format_mmss(hi)}"
                    ),
                    "source": "approx",
                }
            )

    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        st = _floatish(sc.get("start"))
        en = _floatish(sc.get("end"))
        if en <= st:
            continue
        sc_dur = en - st
        pace = str(sc.get("pace") or "").strip().lower()
        motion = str(sc.get("motion") or "").strip().lower()
        if sc_dur > STATIC_SCENE_NORM_SEC and (
            pace in {"static", "slow"} or motion == "static"
        ):
            excess = sc_dur - STATIC_SCENE_NORM_SEC
            risks.append(
                {
                    "start": st,
                    "end": en,
                    "t": st + sc_dur / 2.0,
                    "weight": 1.0 + excess * 0.3,
                    "severity": min(1.0, excess / 6.0),
                    "reason_vi": f"cảnh tĩnh dài {_format_mmss(st)}–{_format_mmss(en)}",
                    "source": "scene",
                }
            )

    for i in range(1, len(scenes)):
        prev = scenes[i - 1] if isinstance(scenes[i - 1], dict) else {}
        curr = scenes[i] if isinstance(scenes[i], dict) else {}
        if not prev or not curr:
            continue
        if (
            str(prev.get("type") or "") == str(curr.get("type") or "")
            and str(prev.get("subject") or "") == str(curr.get("subject") or "")
            and str(prev.get("type") or "").strip()
        ):
            st = _floatish(curr.get("start"))
            en = _floatish(curr.get("end"))
            if en > st:
                risks.append(
                    {
                        "start": st,
                        "end": en,
                        "t": st,
                        "weight": 0.9,
                        "severity": 0.55,
                        "reason_vi": (
                            f"lặp cảnh {_format_mmss(st)}–{_format_mmss(en)} "
                            f"({curr.get('type') or 'cùng chủ thể'})"
                        ),
                        "source": "scene",
                    }
                )

    if ha.get("hook_body_contract") is False:
        risks.append(
            {
                "start": 0.0,
                "end": min(OPENING_WINDOW_SEC, dur),
                "t": 1.5,
                "weight": 1.4,
                "severity": 0.75,
                "reason_vi": "cam kết hook chưa trả trong 3s đầu",
                "source": "scene",
            }
        )
    first_speech = ha.get("first_speech_at")
    try:
        fs = float(first_speech) if first_speech is not None else None
    except (TypeError, ValueError):
        fs = None
    if fs is not None and fs > 2.0:
        risks.append(
            {
                "start": 0.0,
                "end": min(fs, dur),
                "t": fs / 2.0,
                "weight": 1.1,
                "severity": 0.65,
                "reason_vi": f"lời đầu tiên muộn (~{_format_mmss(fs)})",
                "source": "scene",
            }
        )

    face_at = ha.get("face_appears_at")
    try:
        fa = float(face_at) if face_at is not None else None
    except (TypeError, ValueError):
        fa = None
    weak_open = str(ha.get("first_frame_type") or "").strip().lower() in {
        "product",
        "text",
        "b_roll",
        "b-roll",
        "logo",
    }
    if fa is not None and fa > 1.5:
        risks.append(
            {
                "start": 0.0,
                "end": min(fa, dur),
                "t": fa / 2.0,
                "weight": 1.0 + (fa - 1.0) * 0.2,
                "severity": min(1.0, fa / 3.0),
                "reason_vi": f"mặt xuất hiện muộn (~{_format_mmss(fa)})",
                "source": "scene",
            }
        )
    elif weak_open:
        risks.append(
            {
                "start": 0.0,
                "end": min(OPENING_WINDOW_SEC, dur),
                "t": 1.0,
                "weight": 0.85,
                "severity": 0.5,
                "reason_vi": "mở đầu yếu (không có mặt người ngay)",
                "source": "scene",
            }
        )

    if isinstance(hook_timeline, list):
        payoff_events = [
            e
            for e in hook_timeline
            if isinstance(e, dict)
            and str(e.get("event") or "") in {"reveal", "product_enter"}
        ]
        for ev in payoff_events:
            try:
                t_ev = float(ev.get("t"))
            except (TypeError, ValueError):
                continue
            if t_ev > OPENING_WINDOW_SEC:
                risks.append(
                    {
                        "start": OPENING_WINDOW_SEC,
                        "end": min(t_ev, dur),
                        "t": (OPENING_WINDOW_SEC + t_ev) / 2.0,
                        "weight": 0.95,
                        "severity": 0.6,
                        "reason_vi": f"payoff muộn sau {_format_mmss(t_ev)}",
                        "source": "scene",
                    }
                )

    if not risks:
        risks.append(
            {
                "start": 0.0,
                "end": min(OPENING_WINDOW_SEC, dur),
                "t": 1.0,
                "weight": 0.5,
                "severity": 0.35,
                "reason_vi": "rủi ro mở đầu mặc định (FYP scroll-stop)",
                "source": "approx",
            }
        )
    return risks


def _allocate_curve_from_risks(
    duration_sec: float,
    *,
    end_pct: float,
    mid_lift: float,
    risks: list[dict[str, Any]],
    n_points: int,
) -> tuple[list[dict[str, float]], list[dict[str, Any]]]:
    dur = max(float(duration_sec), 0.1)
    bins = max(n_points * 4, 40)
    bin_weights = [0.0] * bins
    bin_len = dur / max(bins - 1, 1)

    for risk in risks:
        w = float(risk.get("weight") or 0.0)
        if w <= 0:
            continue
        lo = max(0.0, float(risk.get("start") or 0.0))
        hi = min(dur, float(risk.get("end") or lo))
        i0 = max(0, int(lo / bin_len))
        i1 = min(bins - 1, int(hi / bin_len))
        span = max(i1 - i0 + 1, 1)
        share = w / span
        for i in range(i0, i1 + 1):
            bin_weights[i] += share

    total_w = sum(bin_weights) or 1.0
    drop_budget = 100.0 - end_pct
    fine: list[dict[str, float]] = []
    pct = 100.0
    allocated: list[float] = []
    for i in range(bins):
        t = dur * i / max(bins - 1, 1)
        drop = drop_budget * (bin_weights[i] / total_w)
        allocated.append(drop)
        u = i / max(bins - 1, 1)
        bump = mid_lift * 2.0 * u * (1.0 - u)
        pct = max(end_pct, pct - drop + bump * 0.15)
        fine.append({"t": round(t, 3), "pct": round(min(100.0, pct), 2)})

    for i in range(1, len(fine)):
        if fine[i]["pct"] > fine[i - 1]["pct"] + 1.5:
            fine[i]["pct"] = fine[i - 1]["pct"]

    fine[-1]["pct"] = round(end_pct, 2)

    out: list[dict[str, float]] = []
    for i in range(n_points):
        t = dur * i / max(n_points - 1, 1)
        idx = min(bins - 1, int(round(t / bin_len)))
        out.append({"t": round(t, 3), "pct": fine[idx]["pct"]})

    risk_ranked = sorted(
        risks,
        key=lambda r: float(r.get("weight") or 0.0) * float(r.get("severity") or 0.5),
        reverse=True,
    )
    risk_events: list[dict[str, Any]] = []
    for r in risk_ranked[:3]:
        risk_events.append(
            {
                "t": round(float(r.get("t") or 0.0), 2),
                "severity": round(float(r.get("severity") or 0.5), 2),
                "reason_vi": str(r.get("reason_vi") or "").strip(),
                "source": str(r.get("source") or "approx"),
            }
        )
    return out, risk_events


def model_retention_curve_from_structure(
    duration_sec: float,
    scenes: list[dict[str, Any]],
    *,
    niche_median_retention: float | None = None,
    breakout_multiplier: float | None = None,
    asr_segments: list[dict[str, Any]] | None = None,
    hook_timeline: list[dict[str, Any]] | None = None,
    hook_analysis: dict[str, Any] | None = None,
    audio_track_role: str | None = None,
    n_points: int = 20,
) -> tuple[list[dict[str, float]], list[dict[str, Any]]]:
    """Structure-driven attention-risk curve + top risk events."""
    dur = max(float(duration_sec), 0.1)
    scene_list = [s for s in (scenes or []) if isinstance(s, dict)]
    end_pct, mid_lift = _retention_end_pct(niche_median_retention, breakout_multiplier)
    risks = _collect_structural_risks(
        dur,
        scene_list,
        asr_segments=asr_segments,
        hook_timeline=hook_timeline,
        hook_analysis=hook_analysis,
        audio_track_role=audio_track_role,
    )
    return _allocate_curve_from_risks(
        dur,
        end_pct=end_pct,
        mid_lift=mid_lift,
        risks=risks,
        n_points=n_points,
    )
