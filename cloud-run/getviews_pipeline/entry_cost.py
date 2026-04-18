"""Entry-cost heuristic — how hard is this video to replicate?

Seller/creator question: "Can I shoot this tonight, or do I need a studio?"

Derived from fields the extraction already returns — no extra Gemini call,
no EnsembleData unit. Feeds directly into trend_spike / content_directions
responses so every reference video carries an easy/medium/hard badge.

Pure function. Unit-tested in tests/test_entry_cost.py.
"""

from __future__ import annotations

from typing import Any, Literal

EntryCost = Literal["easy", "medium", "hard"]


def _count_distinct_scene_types(scenes: list[dict[str, Any]]) -> int:
    return len({str(s.get("type") or "") for s in scenes if s.get("type")})


def score_entry_cost(analysis: dict[str, Any]) -> tuple[EntryCost, list[str]]:
    """Return (tier, reasons).

    Rules — additive, each trigger bumps the score. Cap at 'hard'.
      +1  transitions_per_second > 1.5   (heavy editing required)
      +1  >= 3 distinct scene types      (implies multiple shot setups)
      +1  >= 4 scenes                    (moderate shoot complexity)
      +1  >= 8 scenes                    (production intensity)
      +1  energy_level == "high"         (fast pacing = more edits)
      +1  >= 5 text overlays             (motion graphics work)

    Score mapping:
      0-1 → easy    (phone + 1 take)
      2-3 → medium  (some editing or 2-3 setups)
      4+  → hard    (production + motion graphics)
    """
    reasons: list[str] = []
    score = 0

    tps = float(analysis.get("transitions_per_second") or 0)
    if tps > 1.5:
        score += 1
        reasons.append(f"{tps:.1f} chuyển cảnh mỗi giây — cần nhiều cut")

    scenes = analysis.get("scenes") or []
    scene_count = len(scenes)
    scene_types = _count_distinct_scene_types(scenes)
    if scene_types >= 3:
        score += 1
        reasons.append(f"{scene_types} kiểu cảnh — nhiều góc máy")
    if scene_count >= 4:
        score += 1
        reasons.append(f"{scene_count} cảnh — cần dựng phim")
    if scene_count >= 8:
        score += 1
        reasons.append("Nhiều cảnh dày đặc — mất thời gian quay")

    energy = str(analysis.get("energy_level") or "").lower()
    if energy == "high":
        score += 1
        reasons.append("Năng lượng cao — nhịp nhanh")

    overlays = analysis.get("text_overlays") or []
    if len(overlays) >= 5:
        score += 1
        reasons.append(f"{len(overlays)} text overlay — cần motion graphics")

    if score <= 1:
        tier: EntryCost = "easy"
    elif score <= 3:
        tier = "medium"
    else:
        tier = "hard"

    return tier, reasons


__all__ = ["EntryCost", "score_entry_cost"]
