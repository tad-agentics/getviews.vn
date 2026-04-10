#!/usr/bin/env python3
"""Print raw ``image_post_info`` from EnsembleData for a TikTok URL (same path as ``get_tiktok_metadata``).

Usage (from repo root)::

    export ENSEMBLEDATA_API_TOKEN=...
    python3 scripts/inspect_carousel_aweme.py 'https://www.tiktok.com/@user/photo/123...'

Confirms ``aweme_detail["image_post_info"]`` and per-slide keys (``display_image.url_list`` vs others).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Repo root on sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from getviews_pipeline import ensemble  # noqa: E402


def _short_preview(obj: Any, max_len: int = 12000) -> str:
    s = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    if len(s) > max_len:
        return s[:max_len] + f"\n... ({len(s)} chars total, truncated)"
    return s


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url", help="TikTok post URL (photo carousel or any post)")
    args = p.parse_args()

    aweme = await ensemble.fetch_post_info(args.url)
    print("aweme_type:", aweme.get("aweme_type"))
    print("aweme_id:", aweme.get("aweme_id"))
    print()
    ipi = aweme.get("image_post_info")
    print("image_post_info is None:", ipi is None)
    print("image_post_info preview:")
    print(_short_preview(ipi))
    print()

    if isinstance(ipi, dict):
        imgs = ipi.get("images")
        print("images: type =", type(imgs).__name__, "len =", len(imgs) if isinstance(imgs, list) else None)
        if isinstance(imgs, list) and imgs:
            for i, item in enumerate(imgs[:3]):
                print(f"\n--- images[{i}] ---")
                if not isinstance(item, dict):
                    print("  (not a dict)", repr(item)[:200])
                    continue
                print("  keys:", sorted(item.keys()))
                di = item.get("display_image")
                print("  display_image:", type(di).__name__, end="")
                if isinstance(di, dict):
                    print(", keys:", sorted(di.keys()))
                    ul = di.get("url_list")
                    if isinstance(ul, list) and ul:
                        print("  display_image.url_list[0][:120]:", (ul[0] or "")[:120])
                else:
                    print()
                ul2 = item.get("url_list")
                if ul2:
                    print("  item.url_list present, len:", len(ul2) if isinstance(ul2, list) else type(ul2))

    print("\ndetect_content_type:", ensemble.detect_content_type(aweme))
    print("extract_image_url_lists slide count:", len(ensemble.extract_image_url_lists(aweme)))


if __name__ == "__main__":
    asyncio.run(main())
