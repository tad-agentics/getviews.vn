#!/usr/bin/env python3
"""Backfill cross-niche ingest rows to in-niche HI-11 class assignment.

Reads ``analysis_json.niche_classification`` at corpus root (batch ingest shape),
recomputes ``content_class_id`` using loop primary creator_niche + format_axis.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# cloud-run/ on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from getviews_pipeline.corpus_ingest import _GEMINI_NICHE_CONFIDENCE_FLOOR
from getviews_pipeline.junction_content_class import (
    content_class_id_for_creator_niche_format,
    creator_niche_has_content_class,
    primary_creator_niche_id_for_content_class,
)
from getviews_pipeline.profile_niches import (
    CREATOR_NICHE_ID_TO_SLUG,
    creator_niche_id_for_legacy_niche,
)
from getviews_pipeline.two_axis_taxonomy import junction_has_pair

CROSS_NICHE_SQL = """
SELECT v.video_id,
  v.ingest_loop_content_class_id AS loop_cc,
  v.content_class_id AS old_cc,
  v.ingest_loop_niche_id,
  v.analysis_json->'niche_classification' AS nc,
  COALESCE(v.analysis_json->>'content_type', 'video') AS content_type
FROM video_corpus v
WHERE v.created_at >= '2026-05-27 03:00:00+07'::timestamptz
  AND v.created_at < '2026-05-27 07:30:00+07'::timestamptz
  AND v.ingest_loop_content_class_id IS NOT NULL
  AND v.content_class_id IS DISTINCT FROM v.ingest_loop_content_class_id
  AND (
    SELECT creator_niche_id
    FROM creator_niche_content_classes
    WHERE content_class_id = v.ingest_loop_content_class_id AND is_primary
    LIMIT 1
  ) IS DISTINCT FROM (
    SELECT creator_niche_id
    FROM creator_niche_content_classes
    WHERE content_class_id = v.content_class_id AND is_primary
    LIMIT 1
  )
ORDER BY v.video_id;
"""


def _proposed_class(row: dict[str, Any]) -> tuple[int | None, str]:
    loop_cc = row.get("loop_cc")
    loop_nid = row.get("ingest_loop_niche_id")
    nc = row.get("nc") or {}
    if not isinstance(nc, dict):
        nc = {}

    loop_cn = primary_creator_niche_id_for_content_class(
        int(loop_cc) if loop_cc is not None else None,
    )
    if loop_cn is None and loop_nid is not None:
        loop_cn = creator_niche_id_for_legacy_niche(int(loop_nid))
    if loop_cn is None:
        return (int(loop_cc) if loop_cc is not None else None, "fallback_loop_no_cn")

    loop_slug = CREATOR_NICHE_ID_TO_SLUG.get(loop_cn)
    if not loop_slug:
        return (int(loop_cc) if loop_cc is not None else None, "fallback_no_slug")

    try:
        conf = float(nc.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if conf < _GEMINI_NICHE_CONFIDENCE_FLOOR:
        return (int(loop_cc) if loop_cc is not None else None, "fallback_low_conf")

    content_type = str(row.get("content_type") or "video")
    is_carousel = content_type == "carousel"
    if is_carousel:
        fmt_raw = nc.get("carousel_format_axis") or nc.get("format_axis")
    else:
        fmt_raw = nc.get("format_axis")
    fmt_axis = str(fmt_raw).strip() if fmt_raw is not None else ""
    if not fmt_axis or not junction_has_pair(loop_slug, fmt_axis):
        return (int(loop_cc) if loop_cc is not None else None, "fallback_junction_miss")

    cc_id = content_class_id_for_creator_niche_format(loop_cn, fmt_axis)
    if cc_id is None or not creator_niche_has_content_class(loop_cn, cc_id):
        return (int(loop_cc) if loop_cc is not None else None, "fallback_no_cc")

    return int(cc_id), "in_niche_route"


def _fetch_rows(client: Any) -> list[dict[str, Any]]:
    client.rpc("exec_sql", {}).execute()  # not available
    raise NotImplementedError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--input", type=Path, help="JSON array from Supabase export")
    args = parser.parse_args()

    rows: list[dict[str, Any]]
    if args.input and args.input.is_file():
        rows = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            print(
                "Need --input JSON or SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY",
                file=sys.stderr,
            )
            return 2
        from supabase import create_client

        client = create_client(url, key)
        # PostgREST cannot run arbitrary SQL; use REST filter approximation
        q = (
            client.table("video_corpus")
            .select(
                "video_id, ingest_loop_content_class_id, content_class_id, "
                "ingest_loop_niche_id, analysis_json, created_at"
            )
            .gte("created_at", "2026-05-26T20:00:00Z")
            .lt("created_at", "2026-05-27T00:30:00Z")
            .execute()
        )
        raw = q.data or []
        rows = []
        for r in raw:
            loop_cc = r.get("ingest_loop_content_class_id")
            old_cc = r.get("content_class_id")
            if loop_cc is None or old_cc is None or loop_cc == old_cc:
                continue
            aj = r.get("analysis_json") or {}
            rows.append({
                "video_id": r["video_id"],
                "loop_cc": loop_cc,
                "old_cc": old_cc,
                "ingest_loop_niche_id": r.get("ingest_loop_niche_id"),
                "nc": aj.get("niche_classification"),
                "content_type": aj.get("content_type") or "video",
            })
        # Filter cross-niche in Python
        filtered: list[dict[str, Any]] = []
        for r in rows:
            loop_cn = primary_creator_niche_id_for_content_class(int(r["loop_cc"]))
            old_cn = primary_creator_niche_id_for_content_class(int(r["old_cc"]))
            if loop_cn is not None and old_cn is not None and loop_cn != old_cn:
                filtered.append(r)
        rows = filtered

    plans: list[dict[str, Any]] = []
    for row in rows:
        new_cc, reason = _proposed_class(row)
        if new_cc is None:
            continue
        plans.append({
            **row,
            "new_cc": new_cc,
            "reason": reason,
            "changed": int(new_cc) != int(row["old_cc"]),
            "matches_loop": int(new_cc) == int(row["loop_cc"]),
        })

    changed = [p for p in plans if p["changed"]]
    print(f"rows={len(plans)} would_change={len(changed)}")
    for p in changed[:5]:
        print(
            f"  {p['video_id']} {p['old_cc']} -> {p['new_cc']} "
            f"({p['reason']}) loop={p['loop_cc']}"
        )
    if len(changed) > 5:
        print(f"  ... +{len(changed) - 5} more")

    spotlight = "7643982250861759764"
    for p in plans:
        if p["video_id"] == spotlight:
            print(
                f"\nspotlight {spotlight}: {p['old_cc']} -> {p['new_cc']} "
                f"reason={p['reason']} loop_cc={p['loop_cc']} "
                f"fmt={(p.get('nc') or {}).get('format_axis')}"
            )

    out_path = (
        Path(__file__).resolve().parents[2]
        / "artifacts/issues/backfill-cross-niche-plan.json"
    )
    out_path.write_text(
        json.dumps(
            {"generated_at": datetime.now(UTC).isoformat(), "plans": plans},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out_path}")

    if not args.apply:
        print("dry-run only (pass --apply to update)")
        return 0

    url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required for --apply", file=sys.stderr)
        return 2
    from supabase import create_client

    client = create_client(url, key)
    ok = 0
    for p in changed:
        loop_cn = primary_creator_niche_id_for_content_class(int(p["loop_cc"]))
        payload: dict[str, Any] = {"content_class_id": p["new_cc"]}
        if loop_cn is not None:
            payload["inferred_creator_niche_id"] = loop_cn
        client.table("video_corpus").update(payload).eq("video_id", p["video_id"]).execute()
        ok += 1
    print(f"applied {ok} updates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
