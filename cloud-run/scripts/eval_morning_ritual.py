#!/usr/bin/env python3
"""Evaluate Daily Ritual prompt v2 quality on real grounding fixtures.

Pipeline (no mock — runs real Gemini + real Supabase):
  1. For each ``--niche-id``, fetch the same grounding the cron would
     (top videos in niche × 7d, fallback to 30d).
  2. Build the prompt via ``_build_prompt`` (v2 with mechanism vocab +
     few-shot + median anchors).
  3. Call Gemini, get a ``RitualBundle`` (3 scripts).
  4. Score against the rubric below, write a Markdown report.

Rubric (heuristic, deterministic — no LLM judge):
  - hook_diversity: 3 distinct hook_type_en (max 3)
  - mechanism_named: each why_works mentions one of the 7 mechanism keys
  - title_length_ok: 30-90 chars
  - title_has_niche_anchor: title contains a token also present in any
    grounding ``hook_phrase`` or ``creator_handle`` (proxy for "niche-specific")
  - no_forbidden_clichés: title + why_works clean of the banned phrase list
  - retention_in_band: retention_est_pct inside the adequacy band
  - shot_count_near_median: |shot_count - median| ≤ 2
  - length_near_median: |length_sec - median| ≤ 10

Usage (from ``cloud-run/``):

    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... GEMINI_API_KEY=... \\
    python3 scripts/eval_morning_ritual.py --niche-id 2 --niche-id 4 --niche-id 13

    # Write to a specific path
    python3 scripts/eval_morning_ritual.py --niche-id 2 --out /tmp/ritual-eval.md

After running, paste the Markdown into a PR comment / artifacts/qa-reports/
to baseline the prompt — re-run after each prompt tune to measure delta.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("ritual_eval")


_MECHANISMS = (
    "curiosity_gap", "social_proof", "identification",
    "contrarian_take", "before_after_promise",
    "status_anchor", "fomo_loss",
)

_FORBIDDEN = (
    "tính năng ẩn", "bí mật không ai nói", "sự thật shock",
    "chỉ 1%", "hack não", "đừng bỏ qua", "xem ngay kẻo muộn",
    "triệu view", "bùng nổ", "công thức vàng",
)

_ADEQUACY_BANDS: dict[str, tuple[int, int]] = {
    "none":           (40, 55),
    "thin":           (45, 60),
    "reference_pool": (50, 70),
    "basic_citation": (55, 72),
    "niche_norms":    (60, 75),
}


def _score_script(
    s: dict[str, Any],
    grounding: list[dict[str, Any]],
    median_shot_count: int,
    median_length_sec: int,
    adequacy: str,
) -> dict[str, Any]:
    title = s.get("title_vi") or ""
    why = s.get("why_works") or ""
    title_lc, why_lc = title.lower(), why.lower()
    blob = f"{title_lc} {why_lc}"

    mechanism_named = any(m in why for m in _MECHANISMS)

    # Niche-anchor proxy: at least 1 word from title appears in any grounding
    # hook_phrase or creator_handle (≥ 4 chars to avoid stop words).
    title_words = {w for w in re.findall(r"\w{4,}", title.lower())}
    grounding_blob = " ".join(
        ((v.get("hook_phrase") or "") + " " + (v.get("creator_handle") or "")).lower()
        for v in grounding
    )
    title_has_niche_anchor = any(w in grounding_blob for w in title_words)

    no_forbidden = not any(p in blob for p in _FORBIDDEN)

    rt_lo, rt_hi = _ADEQUACY_BANDS.get(adequacy, _ADEQUACY_BANDS["thin"])
    retention_in_band = rt_lo <= int(s.get("retention_est_pct") or 0) <= rt_hi

    shot_diff = abs(int(s.get("shot_count") or 0) - median_shot_count)
    len_diff = abs(int(s.get("length_sec") or 0) - median_length_sec)

    return {
        "mechanism_named": mechanism_named,
        "title_length_ok": 30 <= len(title) <= 90,
        "title_has_niche_anchor": title_has_niche_anchor,
        "no_forbidden": no_forbidden,
        "retention_in_band": retention_in_band,
        "shot_count_near_median": shot_diff <= 2,
        "length_near_median": len_diff <= 10,
        "shot_diff": shot_diff,
        "length_diff": len_diff,
    }


def _eval_one_niche(client: Any, niche_id: int) -> dict[str, Any]:
    from getviews_pipeline.morning_ritual import (
        _build_prompt,
        _fetch_grounding_videos,
        _median,
        RitualBundle,
        MIN_GROUNDING_VIDEOS,
    )
    from getviews_pipeline.config import (
        GEMINI_SYNTHESIS_MODEL,
        GEMINI_SYNTHESIS_FALLBACKS,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _response_text,
        _normalize_response,
    )
    from google.genai import types  # type: ignore[import-untyped]

    niche_row = (
        client.table("niche_taxonomy")
        .select("name_vn, name_en")
        .eq("id", niche_id)
        .single()
        .execute()
        .data or {}
    )
    niche_name = niche_row.get("name_vn") or niche_row.get("name_en") or f"#{niche_id}"

    videos, adequacy = _fetch_grounding_videos(client, niche_id, [])
    if len(videos) < MIN_GROUNDING_VIDEOS:
        return {
            "niche_id": niche_id,
            "niche_name": niche_name,
            "error": f"thin grounding ({len(videos)} videos) — eval skipped",
        }

    shot_counts = [int(v.get("scene_count")) for v in videos if v.get("scene_count") is not None]
    durations = [int(v.get("video_duration")) for v in videos if v.get("video_duration") is not None]
    med_shot = _median(shot_counts) or 4
    med_len = _median(durations) or 30

    prompt = _build_prompt(niche_name, videos, [], adequacy=adequacy)

    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=RitualBundle.model_json_schema(),
        temperature=0.7,
    )
    raw = _generate_content_models(
        prompt,
        cfg,
        GEMINI_SYNTHESIS_MODEL,
        GEMINI_SYNTHESIS_FALLBACKS,
    )
    bundle_json = json.loads(_response_text(_normalize_response(raw)))
    scripts = bundle_json.get("scripts") or []

    hook_types = [s.get("hook_type_en") for s in scripts]
    diversity = len(set(hook_types))

    per_script = [
        _score_script(s, videos, med_shot, med_len, adequacy)
        for s in scripts
    ]

    return {
        "niche_id": niche_id,
        "niche_name": niche_name,
        "adequacy": adequacy,
        "grounding_count": len(videos),
        "median_shot_count": med_shot,
        "median_length_sec": med_len,
        "scripts": scripts,
        "scores": {
            "hook_diversity": diversity,
            "per_script": per_script,
            "all_three_pass_mechanism": sum(s["mechanism_named"] for s in per_script) == 3,
            "all_three_pass_anchor": sum(s["title_has_niche_anchor"] for s in per_script) == 3,
            "all_three_pass_no_forbidden": sum(s["no_forbidden"] for s in per_script) == 3,
            "all_three_pass_retention_band": sum(s["retention_in_band"] for s in per_script) == 3,
        },
    }


def _format_md(results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append(f"# Daily Ritual prompt eval — {datetime.now(timezone.utc).isoformat()}\n")
    for r in results:
        lines.append(f"## Niche {r.get('niche_id')} — {r.get('niche_name')}\n")
        if r.get("error"):
            lines.append(f"⚠️ {r['error']}\n")
            continue
        lines.append(f"- adequacy: `{r['adequacy']}`")
        lines.append(f"- grounding_count: {r['grounding_count']}")
        lines.append(f"- median shot_count: {r['median_shot_count']} · length: {r['median_length_sec']}s")
        s = r["scores"]
        lines.append(f"- hook_diversity: {s['hook_diversity']}/3")
        lines.append(f"- 3/3 mechanism_named: {'✓' if s['all_three_pass_mechanism'] else '✗'}")
        lines.append(f"- 3/3 niche_anchor: {'✓' if s['all_three_pass_anchor'] else '✗'}")
        lines.append(f"- 3/3 no_forbidden: {'✓' if s['all_three_pass_no_forbidden'] else '✗'}")
        lines.append(f"- 3/3 retention_in_band: {'✓' if s['all_three_pass_retention_band'] else '✗'}\n")
        for i, sc in enumerate(r["scripts"], 1):
            ps = s["per_script"][i - 1]
            lines.append(f"### Script {i} — `{sc.get('hook_type_en')}`")
            lines.append(f"> {sc.get('title_vi')}\n")
            lines.append(f"_{sc.get('why_works')}_\n")
            lines.append(
                f"meta: retention {sc.get('retention_est_pct')}% · "
                f"{sc.get('shot_count')} shot ({'±' + str(ps['shot_diff'])}) · "
                f"{sc.get('length_sec')}s ({'±' + str(ps['length_diff'])})"
            )
            checks = [
                ("mechanism_named", ps["mechanism_named"]),
                ("title_length_ok", ps["title_length_ok"]),
                ("title_has_niche_anchor", ps["title_has_niche_anchor"]),
                ("no_forbidden", ps["no_forbidden"]),
                ("retention_in_band", ps["retention_in_band"]),
                ("shot_count_near_median", ps["shot_count_near_median"]),
                ("length_near_median", ps["length_near_median"]),
            ]
            checks_md = " · ".join(f"{n}: {'✓' if v else '✗'}" for n, v in checks)
            lines.append(f"checks: {checks_md}\n")
        lines.append("---\n")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval Daily Ritual prompt v2")
    parser.add_argument(
        "--niche-id", type=int, action="append", required=True,
        help="One or more niche_taxonomy.id values to evaluate.",
    )
    parser.add_argument(
        "--out", type=str, default=None,
        help="Path to write Markdown report. Default = stdout.",
    )
    args = parser.parse_args()

    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    results = [_eval_one_niche(client, nid) for nid in args.niche_id]
    md = _format_md(results)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        logger.info("wrote eval report to %s", args.out)
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
