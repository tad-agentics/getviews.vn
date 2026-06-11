"""Guard against config.py ↔ settings.py drift (audit 2026-06-10 hardening).

Cloud Run grew two config systems: module-level constants in ``config.py``
(read by the enforcement paths, e.g. ``gemini_cost.check_gemini_daily_budget``)
and the pydantic ``Settings`` singleton (read by startup warnings and newer
code). The Gemini budget fields exist in BOTH — and they drifted once
already: settings claimed "unlimited / log-only" while config enforced a
$15/day cap, so the startup warning lied about live behaviour.

Until the two are merged, this test pins the duplicated fields together.
If you change a default in one file, change the other in the same commit.
"""

from __future__ import annotations

from getviews_pipeline import config
from getviews_pipeline.settings import settings


def test_gemini_budget_fields_match_config() -> None:
    # Both sides read the same env vars, so effective-value equality is the
    # contract that matters (covers both bare defaults and env-overridden CI).
    assert settings.gemini_daily_usd_max == config.GEMINI_DAILY_USD_MAX, (
        "settings.gemini_daily_usd_max != config.GEMINI_DAILY_USD_MAX — the "
        "startup warning and the actual enforcement disagree. Update both "
        "defaults in the same commit (settings.py:81 / config.py GEMINI_DAILY_USD_MAX)."
    )
    assert settings.gemini_daily_usd_enforce == config.GEMINI_DAILY_USD_ENFORCE, (
        "settings.gemini_daily_usd_enforce != config.GEMINI_DAILY_USD_ENFORCE — "
        "the startup warning and the actual enforcement disagree. Update both "
        "defaults in the same commit."
    )
