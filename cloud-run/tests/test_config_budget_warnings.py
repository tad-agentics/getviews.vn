"""Boot-time budget warnings in config._warn_unbounded_budgets."""

from __future__ import annotations

import logging

import pytest

from getviews_pipeline import config as gv_config


def test_warn_unbounded_budgets_logs_tikhub_when_cap_zero(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(gv_config, "TIKHUB_DOUYIN_DAILY_REQUEST_MAX", 0)
    with caplog.at_level(logging.WARNING, logger=gv_config.logger.name):
        gv_config._warn_unbounded_budgets()
    assert any(
        "TIKHUB_DOUYIN_DAILY_REQUEST_MAX=0" in record.message
        for record in caplog.records
    )


def test_creator_slug_and_hook_prefers_hook_type_over_type() -> None:
    from getviews_pipeline.pipelines import _creator_slug_and_hook_from_user_res

    slug, hook = _creator_slug_and_hook_from_user_res({
        "analysis": {
            "niche_classification": {"creator_niche_slug": "tech"},
            "hook_analysis": {"type": "", "hook_type": "bold_claim"},
        },
    })
    assert slug == "tech"
    assert hook == "bold_claim"
