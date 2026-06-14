"""Parity guard: contract params must match ``synthesize_diagnosis_v2``."""

from __future__ import annotations

import inspect

import pytest

from getviews_pipeline.diagnosis_synthesis_contract import diagnosis_synthesis_kwargs
from getviews_pipeline.gemini import synthesize_diagnosis_v2


def _param_names(fn) -> set[str]:
    return set(inspect.signature(fn).parameters)


def test_contract_param_names_match_synthesize_diagnosis_v2() -> None:
    engine = _param_names(synthesize_diagnosis_v2)
    contract = _param_names(diagnosis_synthesis_kwargs)
    assert contract == engine, (
        f"drift: engine-only={engine - contract}, contract-only={contract - engine}"
    )


def test_contract_returns_all_engine_keys() -> None:
    kwargs = diagnosis_synthesis_kwargs(
        content_format="tutorial",
        niche_name="thoi_trang",
        corpus_size=100,
        niche_meta={},
        reference_videos=[],
        user_analysis={},
        user_stats={"views": 1},
        collapsed_questions=None,
        wants_directions=False,
        layer0_context="",
        corpus_citation="",
        persona_block="",
        performance_tier="unknown",
        channel_context=None,
        errors=None,
        reference_evidence_block="",
        creator_format_history_block="",
        cross_format_signal=None,
        niche_posting_context_block="",
        comment_radar=None,
        hook_effectiveness=None,
        addressing_mode="third_party",
        video_creator_handle=None,
    )
    assert set(kwargs.keys()) == _param_names(synthesize_diagnosis_v2)


def test_contract_missing_kwarg_raises_type_error() -> None:
    with pytest.raises(TypeError):
        diagnosis_synthesis_kwargs(content_format="x")  # type: ignore[call-arg]


def test_contract_params_are_required_keyword_only() -> None:
    """The drift guard relies on every param being required + keyword-only.

    A default on any contract param would let a call site omit it without a
    TypeError, silently weakening the guarantee this module exists to enforce.
    """
    params = inspect.signature(diagnosis_synthesis_kwargs).parameters.values()
    with_defaults = [p.name for p in params if p.default is not inspect.Parameter.empty]
    not_keyword_only = [p.name for p in params if p.kind is not p.KEYWORD_ONLY]
    assert not with_defaults, f"params must have no defaults: {with_defaults}"
    assert not not_keyword_only, f"params must be keyword-only: {not_keyword_only}"
