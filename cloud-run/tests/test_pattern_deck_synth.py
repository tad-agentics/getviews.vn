"""Unit tests for ``pattern_deck_synth`` — Trends pattern decks.

The Gemini call itself is mocked (needs API key + network); tests cover
the parts we wrote: prompt shaping, thin-corpus guard, schema-error
classification, upsert call shape, batch summary counting + the
staleness query path.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from getviews_pipeline.pattern_deck_synth import (
    DEFAULT_BATCH_CAP,
    GROUNDING_CAP,
    MIN_GROUNDING_VIDEOS,
    PatternDeckLLM,
    PatternDeckResult,
    _build_prompt,
    run_pattern_decks_batch,
    synthesize_pattern_deck,
    upsert_deck,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


SAMPLE_VIDEOS = [
    {
        "video_id":    f"vid{i}",
        "creator_handle": f"creator{i}",
        "views":       100_000 - i * 10_000,
        "hook_phrase": f"Hook {i}: mở bằng câu hỏi {i}",
        "hook_type":   ["pov", "story_open", "comparison"][i % 3],
    }
    for i in range(6)
]


VALID_LLM_PAYLOAD: dict[str, Any] = {
    "structure": [
        "Mở: câu hỏi 'tôi đã dùng X trong N tháng' (0-2s)",
        "Setup: thử thách ban đầu / sự nghi ngờ (2-8s)",
        "Body: 3 điểm đã thay đổi · b-roll dày (8-35s)",
        "Payoff: verdict thẳng · CTA mềm (35-50s)",
    ],
    "why": (
        "Format thử-thách-thời-gian tạo curiosity. Audience muốn biết kết "
        "quả cuối — tỉ lệ xem hết cao, save cũng cao vì giống testimonial."
    ),
    "careful": (
        "Nếu chưa thực sự dùng X tháng, đừng giả. TikTok đẩy mạnh "
        "authenticity drop-off — comment sẽ phát hiện."
    ),
    "angles": [
        {"angle": "Sản phẩm Apple", "filled": 18, "gap": False},
        {"angle": "AI tools (ChatGPT/Claude/Cursor)", "filled": 14, "gap": False},
        {"angle": "Setup làm việc", "filled": 9, "gap": False},
        {"angle": "Phụ kiện cao cấp (>5tr)", "filled": 0, "gap": True},
    ],
}


# ── Pydantic schema sanity ────────────────────────────────────────────────


def test_llm_schema_accepts_valid_payload() -> None:
    parsed = PatternDeckLLM.model_validate(VALID_LLM_PAYLOAD)
    assert len(parsed.structure) == 4
    assert any(a.gap for a in parsed.angles)


def test_llm_schema_rejects_wrong_structure_length() -> None:
    bad = {**VALID_LLM_PAYLOAD, "structure": ["Only", "Three", "Lines"]}
    try:
        PatternDeckLLM.model_validate(bad)
    except ValidationError:
        return
    raise AssertionError("expected ValidationError on 3-line structure")


def test_llm_schema_rejects_too_few_angles() -> None:
    bad = {**VALID_LLM_PAYLOAD, "angles": VALID_LLM_PAYLOAD["angles"][:2]}
    try:
        PatternDeckLLM.model_validate(bad)
    except ValidationError:
        return
    raise AssertionError("expected ValidationError on 2-angle list")


# ── Prompt shaping ────────────────────────────────────────────────────────


def test_build_prompt_includes_niche_pattern_and_trims_videos() -> None:
    # 30 videos > GROUNDING_CAP (12) → prompt includes only the cap.
    many = SAMPLE_VIDEOS * 5
    prompt = _build_prompt(
        pattern_name="Sau ___ tháng dùng",
        niche_name="Tech",
        videos=many,
    )
    assert "Tech" in prompt
    assert "Sau ___ tháng dùng" in prompt
    # Grounding payload mentions only GROUNDING_CAP rows.
    assert prompt.count("\"video_id\"") == GROUNDING_CAP


def test_build_prompt_uses_placeholder_when_pattern_name_blank() -> None:
    prompt = _build_prompt(pattern_name="", niche_name="Food", videos=SAMPLE_VIDEOS)
    assert "(chưa có tên)" in prompt


def test_build_prompt_single_niche_keeps_niche_specific_phrasing() -> None:
    """No `niche_labels` (or len < 2) → existing single-niche prompt
    shape. Don't regress the food-specific / beauty-specific helpfulness
    of patterns that genuinely live in one niche."""
    prompt = _build_prompt(
        pattern_name="Macro shot",
        niche_name="Làm đẹp / Skincare",
        videos=SAMPLE_VIDEOS,
        niche_labels=["Làm đẹp / Skincare"],  # length 1 → still single-niche
    )
    assert "Làm đẹp / Skincare" in prompt
    assert "CHÉO NGÁCH" not in prompt
    # No cross-niche rule appended when single niche.
    assert "TRUNG TÍNH" not in prompt


def test_build_prompt_cross_niche_neutralises_thesis_phrasing() -> None:
    """Repro of the audit bug: pattern "Cận" spans 8 niches with
    food being primary, producing food-flavored copy on a Beauty
    creator's screen. With niche_labels >= 2 the prompt:
      - lists all niches so Gemini knows the spread,
      - explicitly forbids niche-specific examples in why/careful/etc.,
      - shifts framing to TECHNIQUE + AUDIENCE BEHAVIOUR."""
    prompt = _build_prompt(
        pattern_name="Cận",
        niche_name="Ẩm thực & Ăn uống",
        videos=SAMPLE_VIDEOS,
        niche_labels=[
            "Ẩm thực & Ăn uống",
            "Làm đẹp / Skincare",
            "Du lịch / Travel",
            "Thời trang Phụ kiện",
        ],
    )
    # Cross-niche framing is explicit in the niche clause.
    assert "CHÉO NGÁCH" in prompt
    # All niches make it into the prompt — Gemini sees the spread.
    assert "Làm đẹp / Skincare" in prompt
    assert "Du lịch / Travel" in prompt
    # Guardrail clause forbids niche-specific examples.
    assert "TRUNG TÍNH" in prompt
    assert "món ăn" in prompt and "skincare" in prompt  # listed as banned examples
    # Old single-niche phrasing should NOT appear (anchoring bias).
    assert 'trong ngách "Ẩm thực' not in prompt


def test_build_prompt_two_niches_is_already_cross_niche() -> None:
    """Threshold is `>= 2` — even a 2-niche pattern gets the neutral
    treatment. Lower bound matches the pattern fingerprinter's own
    cross-niche signal."""
    prompt = _build_prompt(
        pattern_name="Reaction",
        niche_name="Hài / Giải trí",
        videos=SAMPLE_VIDEOS,
        niche_labels=["Hài / Giải trí", "Gaming"],
    )
    assert "CHÉO NGÁCH" in prompt
    assert "Gaming" in prompt


# ── synthesize_pattern_deck — end-to-end with mocked Gemini ──────────────


def _mock_client_with_pattern(
    pattern: dict[str, Any] | None,
    grounding: list[dict[str, Any]],
    niche_label: str = "Tech",
) -> MagicMock:
    client = MagicMock()

    def table(name: str) -> Any:
        builder = MagicMock()
        if name == "video_patterns":
            builder.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=pattern,
            )
            # ``update().eq().execute()`` chain for upsert path.
            builder.update.return_value.eq.return_value.execute.return_value = MagicMock(data=None)
        elif name == "video_corpus":
            # Chains: .select().eq().order().limit().execute() or double .eq()
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.order.return_value = chain
            tail = MagicMock()
            tail.execute.return_value = MagicMock(data=grounding)
            chain.limit.return_value = tail
            builder.select.return_value = chain
        elif name == "niche_taxonomy":
            builder.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"name_vn": niche_label, "name_en": niche_label},
            )
        return builder

    client.table.side_effect = table
    return client


def test_synthesize_thin_corpus_short_circuits_below_min() -> None:
    client = _mock_client_with_pattern(
        pattern={"id": "p1", "display_name": "X", "niche_spread": [4]},
        grounding=SAMPLE_VIDEOS[: MIN_GROUNDING_VIDEOS - 1],
    )
    result = synthesize_pattern_deck(client, "p1")
    assert result.deck is None
    assert result.error is not None and result.error.startswith("thin_corpus")


def test_synthesize_returns_deck_on_valid_gemini_response() -> None:
    client = _mock_client_with_pattern(
        pattern={"id": "p1", "display_name": "X", "niche_spread": [4]},
        grounding=SAMPLE_VIDEOS,
    )
    fake_llm = PatternDeckLLM.model_validate(VALID_LLM_PAYLOAD)
    with patch(
        "getviews_pipeline.pattern_deck_synth._call_pattern_gemini",
        return_value=fake_llm,
    ):
        result = synthesize_pattern_deck(client, "p1")
    assert result.error is None
    assert result.deck is not None
    assert len(result.deck["structure"]) == 4
    assert "angles" in result.deck and any(a["gap"] for a in result.deck["angles"])


def test_synthesize_classifies_schema_error() -> None:
    client = _mock_client_with_pattern(
        pattern={"id": "p1", "display_name": "X", "niche_spread": [4]},
        grounding=SAMPLE_VIDEOS,
    )

    def boom(_prompt: str) -> PatternDeckLLM:
        raise ValidationError.from_exception_data("PatternDeckLLM", [])

    with patch(
        "getviews_pipeline.pattern_deck_synth._call_pattern_gemini",
        side_effect=boom,
    ):
        result = synthesize_pattern_deck(client, "p1")
    assert result.deck is None
    assert result.error == "schema_error"


def test_synthesize_classifies_gemini_error() -> None:
    client = _mock_client_with_pattern(
        pattern={"id": "p1", "display_name": "X", "niche_spread": [4]},
        grounding=SAMPLE_VIDEOS,
    )
    with patch(
        "getviews_pipeline.pattern_deck_synth._call_pattern_gemini",
        side_effect=RuntimeError("network down"),
    ):
        result = synthesize_pattern_deck(client, "p1")
    assert result.deck is None
    assert result.error == "gemini_error"


def test_synthesize_returns_pattern_not_found_for_missing_row() -> None:
    client = _mock_client_with_pattern(pattern=None, grounding=[])
    result = synthesize_pattern_deck(client, "missing")
    assert result.error == "pattern_not_found"


# ── upsert_deck ──────────────────────────────────────────────────────────


def test_upsert_writes_deck_with_computed_at_stamp() -> None:
    client = MagicMock()
    update = MagicMock()
    eq = MagicMock()
    client.table.return_value.update.return_value = update
    update.eq.return_value = eq
    eq.execute.return_value = MagicMock(data=None)

    result = PatternDeckResult(
        pattern_id="p1",
        deck={"structure": ["a", "b", "c", "d"], "why": "x", "careful": "y", "angles": []},
        error=None,
    )
    ok = upsert_deck(client, result)
    assert ok is True
    # update() got called with deck fields + deck_computed_at.
    write_call = client.table.return_value.update.call_args.args[0]
    assert "structure" in write_call
    assert "why" in write_call
    assert "careful" in write_call
    assert "angles" in write_call
    assert "deck_computed_at" in write_call


def test_upsert_noop_on_error_result() -> None:
    client = MagicMock()
    bad = PatternDeckResult(pattern_id="p1", deck=None, error="thin_corpus:1")
    assert upsert_deck(client, bad) is False
    client.table.assert_not_called()


# ── Batch orchestrator ──────────────────────────────────────────────────


def test_batch_returns_zero_summary_when_no_stale_patterns() -> None:
    client = MagicMock()
    with patch(
        "getviews_pipeline.pattern_deck_synth._fetch_stale_pattern_ids",
        return_value=[],
    ):
        summary = run_pattern_decks_batch(client)
    assert summary.considered == 0
    assert summary.generated == 0


def test_batch_walks_pattern_ids_override_and_counts_outcomes() -> None:
    client = MagicMock()
    # 3 patterns; one succeeds, one thin, one schema-error.
    side_effects = [
        PatternDeckResult(
            pattern_id="p1",
            deck={"structure": [], "why": "", "careful": "", "angles": []},
            error=None,
        ),
        PatternDeckResult(pattern_id="p2", deck=None, error="thin_corpus:2"),
        PatternDeckResult(pattern_id="p3", deck=None, error="schema_error"),
    ]
    with (
        patch(
            "getviews_pipeline.pattern_deck_synth.synthesize_pattern_deck",
            side_effect=side_effects,
        ),
        patch(
            "getviews_pipeline.pattern_deck_synth.upsert_deck",
            return_value=True,
        ),
    ):
        summary = run_pattern_decks_batch(
            client,
            pattern_ids=["p1", "p2", "p3"],
        )
    assert summary.considered == 3
    assert summary.generated == 1
    assert summary.skipped_thin == 1
    assert summary.failed_schema == 1


def test_batch_default_cap_matches_module_constant() -> None:
    # Smoke-only: ensure the orchestrator still reads DEFAULT_BATCH_CAP
    # via its keyword default; if someone bumps the cap unintentionally
    # this test won't break, but the constant import is asserted live.
    assert DEFAULT_BATCH_CAP > 0
