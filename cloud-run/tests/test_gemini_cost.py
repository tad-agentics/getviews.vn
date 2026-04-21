"""Phase D.5.1 — gemini_cost helper regression.

Three invariants locked:

1. `estimate_cost` — unknown models route to the zero-cost fallback,
   known models compute against the pricing table, and date-suffixed
   model names (e.g. `gemini-3-flash-preview-04-2026`) still resolve to
   the right base price.

2. `extract_usage` — a real genai response's `usage_metadata` yields
   the correct `(tokens_in, tokens_out)` tuple, and a response without
   the metadata attribute (error paths, mocked fallback models) yields
   zeros without throwing.

3. `log_gemini_call` — builds the row payload the migration expects
   (matching column names + types) and computes cost consistently with
   `estimate_cost` in isolation. The Supabase insert is mocked so the
   test stays offline.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.gemini_cost import (
    MODEL_PRICING_USD_PER_MTOK,
    UNKNOWN_MODEL_PRICE,
    estimate_cost,
    extract_usage,
    log_gemini_call,
    price_for_model,
)


class TestPriceForModel:
    def test_exact_match_returns_table_entry(self) -> None:
        p = price_for_model("gemini-3-flash-lite-preview")
        assert p == MODEL_PRICING_USD_PER_MTOK["gemini-3-flash-lite-preview"]

    def test_date_suffixed_variant_strips_to_base(self) -> None:
        # Google pins `-04-2026` style suffixes on some previews; the price
        # table stays keyed by the base name and the stripper finds it.
        p = price_for_model("gemini-3-flash-preview-04-2026")
        assert p == MODEL_PRICING_USD_PER_MTOK["gemini-3-flash-preview"]

    def test_unknown_model_returns_zero_price_fallback(self) -> None:
        p = price_for_model("some-other-provider-model")
        assert p == UNKNOWN_MODEL_PRICE
        assert p.tokens_in_per_mtok == 0.0
        assert p.tokens_out_per_mtok == 0.0


class TestEstimateCost:
    def test_flash_lite_math_matches_published_rates(self) -> None:
        # 1M in + 1M out on flash-lite: $0.075 + $0.30 = $0.375.
        cost = estimate_cost(
            model_name="gemini-3-flash-lite-preview",
            tokens_in=1_000_000,
            tokens_out=1_000_000,
        )
        assert cost == pytest.approx(0.375, rel=1e-9)

    def test_unknown_model_costs_nothing_but_does_not_raise(self) -> None:
        cost = estimate_cost(
            model_name="made-up-model",
            tokens_in=999,
            tokens_out=1_234,
        )
        assert cost == 0.0

    def test_zero_tokens_costs_zero(self) -> None:
        cost = estimate_cost(
            model_name="gemini-3-flash-preview",
            tokens_in=0,
            tokens_out=0,
        )
        assert cost == 0.0


class TestExtractUsage:
    def test_populated_metadata_yields_correct_pair(self) -> None:
        response = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=1234,
                candidates_token_count=567,
            )
        )
        assert extract_usage(response) == (1234, 567)

    def test_missing_metadata_returns_zeros(self) -> None:
        # Some fallback model paths (or mid-stream errors) produce responses
        # without `usage_metadata`; the helper must not raise — zero-cost
        # rows are preferred over blocking the request.
        response = SimpleNamespace()
        assert extract_usage(response) == (0, 0)

    def test_none_counts_coerce_to_zero(self) -> None:
        response = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=None,
                candidates_token_count=None,
            )
        )
        assert extract_usage(response) == (0, 0)


class TestLogGeminiCall:
    def test_inserts_row_matching_migration_columns(self) -> None:
        captured: dict[str, Any] = {}

        def capture_insert(row: dict[str, Any]) -> None:
            captured.update(row)

        # Patch `_insert_row` at module scope so the daemon thread runs our
        # capture synchronously from the test's perspective. The production
        # code fires-and-forgets, but test-side we join before asserting.
        with patch("getviews_pipeline.gemini_cost._insert_row", side_effect=capture_insert):
            cost = log_gemini_call(
                user_id="user-1",
                call_site="pattern_narrative",
                model_name="gemini-3-flash-preview",
                tokens_in=1000,
                tokens_out=2000,
                duration_ms=450,
                session_id="sess-xyz",
            )
            # Wait briefly for the daemon thread to run.
            for _ in range(50):
                if "call_site" in captured:
                    break
                time.sleep(0.01)

        assert captured["user_id"] == "user-1"
        assert captured["call_site"] == "pattern_narrative"
        assert captured["model_name"] == "gemini-3-flash-preview"
        assert captured["tokens_in"] == 1000
        assert captured["tokens_out"] == 2000
        assert captured["duration_ms"] == 450
        assert captured["session_id"] == "sess-xyz"
        # Cost is computed consistently with estimate_cost (1k in + 2k out
        # on flash-preview = $0.0003 + $0.0024 = $0.0027).
        assert captured["cost_usd"] == pytest.approx(0.0027, rel=1e-9)
        assert cost == pytest.approx(0.0027, rel=1e-9)

    def test_accepts_null_user_id_and_session_id(self) -> None:
        # Batch/cron callers (corpus ingest, niche intelligence) fire with
        # no user context — the row must still persist for aggregate cost.
        captured: dict[str, Any] = {}
        with patch(
            "getviews_pipeline.gemini_cost._insert_row",
            side_effect=lambda row: captured.update(row),
        ):
            log_gemini_call(
                user_id=None,
                call_site="batch_summary",
                model_name="gemini-3-flash-preview",
                tokens_in=500,
                tokens_out=1000,
                duration_ms=300,
            )
            for _ in range(50):
                if "call_site" in captured:
                    break
                time.sleep(0.01)

        assert captured["user_id"] is None
        assert captured["session_id"] is None

    def test_supabase_failure_does_not_propagate(self) -> None:
        # If the service-role insert blows up (bad env, dropped connection),
        # the caller must not see the exception — cost logging is always
        # best-effort.
        with patch(
            "getviews_pipeline.gemini_cost.get_service_client",
            side_effect=RuntimeError("no env"),
        ):
            # Not raising is the contract. No assertion other than "returns".
            log_gemini_call(
                user_id=None,
                call_site="batch_summary",
                model_name="gemini-3-flash-preview",
                tokens_in=10,
                tokens_out=20,
                duration_ms=50,
            )
            # Let the daemon thread's catch-all fire.
            time.sleep(0.05)


class TestWrapperContract:
    """Sanity check that the `_generate_content_models` wrapper still
    accepts the new keyword-only params without breaking its old signature.

    Full end-to-end integration (with a real genai client) lives on the
    deployed service — this test just locks the public shape so a caller
    that doesn't pass `call_site` still compiles and records an `unknown`
    row rather than blowing up.
    """

    def test_signature_accepts_new_kwargs(self) -> None:
        from inspect import signature

        from getviews_pipeline.gemini import _generate_content_models

        params = signature(_generate_content_models).parameters
        assert "call_site" in params
        assert params["call_site"].default == "unknown"
        assert "user_id" in params
        assert "session_id" in params
