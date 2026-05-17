"""§2 Vietnam posting windows (ICT) for golden-hour miss signals."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

_ICT = ZoneInfo("Asia/Ho_Chi_Minh")


def in_vietnam_golden_window(dt: datetime) -> bool:
    """True if *dt* (any tz) falls in a plan §2 \"khung giờ vàng\" band in Vietnam ICT.

    Bands: 06:00–09:00, 11:30–13:30, 18:00–20:00, 22:00–24:00, plus Thursday 19:00–21:00 peak.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(_ICT)
    wd = local.isoweekday()  # Mon=1 … Sun=7
    m = local.hour * 60 + local.minute + local.second / 60.0

    def band(a: float, b: float) -> bool:
        return a <= m < b

    if band(6 * 60, 9 * 60):
        return True
    if band(11.5 * 60, 13.5 * 60):
        return True
    if band(18 * 60, 20 * 60):
        return True
    if band(22 * 60, 24 * 60):
        return True
    if wd == 4 and band(19 * 60, 21 * 60):
        return True
    return False
