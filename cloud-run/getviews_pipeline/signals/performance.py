"""§12 — Commerce conversion metrics (TikTok Shop / seller APIs).

Reads optional ``user_stats["commerce_conversion"]`` or ``shop_order_count`` when
backend fills them. Do not ask Gemini to invent orders — keep extraction null;
merge server-side from API only (see `video_analyze.py`).
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_MIN_VIEWS_FOR_RATE = 1_000


def _parse_commerce_conversion(us: dict[str, Any]) -> dict[str, Any] | None:
    raw = us.get("commerce_conversion")
    if isinstance(raw, dict) and raw:
        return raw
    oc = us.get("shop_order_count")
    if oc is None:
        return None
    try:
        n = int(oc)
    except (TypeError, ValueError):
        return None
    return {"order_count": n}


def _order_count(conv: dict[str, Any]) -> int | None:
    v = conv.get("order_count")
    if v is None:
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def _strong_shop_conversion(order_count: int, views: int) -> bool:
    """High conversion density vs views (plan: 80k views + 300 orders)."""
    if order_count <= 0 or views < _MIN_VIEWS_FOR_RATE:
        return False
    if order_count >= 100:
        return True
    per_1k = order_count * 1000.0 / float(views)
    if per_1k >= 1.0:
        return True
    return order_count >= 40 and per_1k >= 0.85


def _views_underperforming(ctx: dict) -> bool:
    tier = str(ctx.get("performance_tier") or "").lower()
    if tier == "hit":
        return False
    us = ctx.get("user_stats") or {}
    if not isinstance(us, dict):
        return tier in ("flop", "average")
    views = int(us.get("views") or 0)
    cmv_raw = us.get("creator_median_views")
    try:
        cmv = int(cmv_raw) if cmv_raw is not None else None
    except (TypeError, ValueError):
        cmv = None
    if tier in ("flop", "average"):
        return True
    if cmv and cmv > 0 and views > 0 and views < int(cmv * 0.45):
        return True
    return False


def _ctx_is_commercial(ctx: dict) -> bool:
    ua = ctx.get("user_analysis") or {}
    if not isinstance(ua, dict):
        return False
    promo = str(ua.get("promotion_type") or "organic").lower()
    if promo not in ("organic", ""):
        return True
    ci = ua.get("commerce_intent")
    if not isinstance(ci, dict):
        return False
    return str(ci.get("conversion_objective") or "entertainment_first").lower() != "entertainment_first"


def extract_commerce_performance_override_signal(ctx: dict) -> list[Signal]:
    """Salience 1.0 when Shop orders contradict a view-only underperformance read."""
    if not _ctx_is_commercial(ctx):
        return []
    if not _views_underperforming(ctx):
        return []
    us = ctx.get("user_stats") or {}
    if not isinstance(us, dict):
        return []
    conv = _parse_commerce_conversion(us)
    if not conv:
        return []
    orders = _order_count(conv)
    if orders is None or orders <= 0:
        return []
    views = int(us.get("views") or 0)
    if not _strong_shop_conversion(orders, views):
        return []
    per_1k = orders * 1000.0 / float(views) if views else 0.0
    tier = str(ctx.get("performance_tier") or "unknown")
    return [
        Signal(
            id="commerce_performance_conversion_override",
            section_id="commerce",
            taxonomy_ref="§12",
            salience=1.0,
            claim=(
                f"Lượt xem thấp hơn benchmark (tier {tier}) nhưng dữ liệu Shop ghi nhận "
                f"{orders} đơn (~{per_1k:.1f} đơn/1k view) — ưu tiên đánh giá theo chuyển đổi, "
                f"không chỉ view."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=(
                        f"order_count={orders}, views={views}, performance_tier={tier}, "
                        f"orders_per_1k={per_1k:.2f}"
                    ),
                    location="user_stats.commerce_conversion + ctx.performance_tier",
                )
            ],
            suggested_fix=(
                "Coi đây là clip bán tốt: giữ phần đã chuyển đổi (hook/offer/bằng chứng); "
                "mở rộng vòng lặp creative (retarget, biến thể) thay vì phá format vì view thấp."
            ),
        )
    ]
