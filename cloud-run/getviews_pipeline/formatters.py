"""Vietnamese number and time formatters for GetViews synthesis output.

These helpers ensure all user-facing numbers and timeframes follow Vietnamese
conventions: dot separators for thousands, natural phrase-based timeframes.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------

def format_vn(n: int | float) -> str:
    """Format a number with Vietnamese thousand separator (dot).

    Vietnamese uses '.' for thousands and ',' for decimals — opposite of English.

    Examples:
        412     → "412"
        1100    → "1.100"
        46000   → "46.000"
        1623886 → "1.623.886"
    """
    return f"{int(n):,}".replace(",", ".")


# ---------------------------------------------------------------------------
# Timeframe phrases — natural Vietnamese (not literal date-math translations)
# ---------------------------------------------------------------------------

_TIMEFRAME_VI: dict[int, str] = {
    7: "tuần này",
    14: "2 tuần qua",
    30: "tháng này",
    90: "3 tháng qua",
}


def timeframe_vi(days: int) -> str:
    """Return a natural Vietnamese timeframe phrase for a given day window.

    Matches the closest bucket; never returns "30 ngày gần nhất" style.

    Examples:
        7  → "tuần này"
        30 → "tháng này"
        14 → "2 tuần qua"
        60 → "3 tháng qua"  (snaps to nearest bucket above)
    """
    for threshold, phrase in sorted(_TIMEFRAME_VI.items()):
        if days <= threshold:
            return phrase
    return "3 tháng qua"


# ---------------------------------------------------------------------------
# Citation string — assembled for synthesis prompt injection
# ---------------------------------------------------------------------------

def citation_vi(count: int, niche_name: str, days: int) -> str:
    """Build a Vietnamese citation string for synthesis prompt injection.

    Format: "Dựa trên {count} video {niche} {timeframe}"

    Args:
        count:      Number of corpus videos in the niche/window.
        niche_name: Human-readable niche label in Vietnamese (e.g. "review đồ gia dụng").
        days:       Recency window in days.

    Examples:
        citation_vi(412, "skincare", 30)
        → "Dựa trên 412 video skincare tháng này"

        citation_vi(1100, "review đồ gia dụng", 7)
        → "Dựa trên 1.100 video review đồ gia dụng tuần này"
    """
    return f"Dựa trên {format_vn(count)} video {niche_name} {timeframe_vi(days)}"


# ---------------------------------------------------------------------------
# Recency display (for VideoRefCard — P0-4)
# ---------------------------------------------------------------------------

def format_recency_vi(days_ago: int) -> str:
    """Return a natural Vietnamese recency string for a days-ago value.

    Examples:
        0  → "Hôm nay"
        1  → "Hôm qua"
        3  → "3 ngày trước"
        7  → "Tuần trước"
        14 → "2 tuần trước"
        30 → "1 tháng trước"
    """
    if days_ago == 0:
        return "Hôm nay"
    if days_ago == 1:
        return "Hôm qua"
    if days_ago <= 7:
        return f"{days_ago} ngày trước"
    if days_ago <= 14:
        return "Tuần trước"
    if days_ago <= 30:
        weeks = days_ago // 7
        return f"{weeks} tuần trước"
    months = days_ago // 30
    return f"{months} tháng trước"


# ---------------------------------------------------------------------------
# Breakout multiplier (Vietnamese comma decimal)
# ---------------------------------------------------------------------------

def format_breakout_vi(ratio: float) -> str:
    """Format a breakout multiplier with Vietnamese decimal separator (comma).

    Vietnamese uses comma for decimals: "3,2x" not "3.2x".

    Examples:
        3.2  → "3,2x"
        4.0  → "4,0x"
        10.5 → "10,5x"
    """
    return f"{ratio:.1f}x".replace(".", ",")
