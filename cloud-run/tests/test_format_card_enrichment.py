"""Per-card corpus enrichment for format_cards (niche × content_format)."""

from __future__ import annotations

from unittest.mock import patch

from getviews_pipeline.pipelines import enrich_format_cards_from_corpus


@patch("getviews_pipeline.pipelines.fetch_format_corpus_enrichment_sync")
def test_enrich_overwrites_llm_stats_when_corpus_cannot_benchmark(mock_fetch):
    mock_fetch.return_value = (None, None, [])
    cards = [
        {
            "content_format": "haul",
            "view_range": "1 – 9",
            "engagement_rate": "9,99%",
        },
    ]
    out = enrich_format_cards_from_corpus(cards, 2, analyzed_content_format=None)
    mock_fetch.assert_called_once()
    assert "mẫu corpus" in out[0]["view_range"].lower()
    assert out[0]["engagement_rate"] == "—"


@patch("getviews_pipeline.pipelines.fetch_format_corpus_enrichment_sync")
def test_enrich_distinct_corpus_slug_per_card(mock_fetch):
    def _fetch(fmt, nid, example_limit=3):
        return f"vr-{fmt}", f"er-{fmt}", [{"aweme_id": f"x-{fmt}"}]

    mock_fetch.side_effect = _fetch
    cards = [
        {"format_name_vi": "Unboxing x", "mechanism_vi": "đập hộp"},
        {"format_name_vi": "Hướng dẫn", "mechanism_vi": "tutorial"},
    ]
    out = enrich_format_cards_from_corpus(cards, 2, analyzed_content_format="review")
    assert mock_fetch.call_count == 2
    slugs = {c.args[0] for c in mock_fetch.call_args_list}
    assert slugs == {"haul", "tutorial"}
    assert out[0]["view_range"] == "vr-haul"
    assert out[1]["view_range"] == "vr-tutorial"


@patch("getviews_pipeline.pipelines.fetch_format_corpus_enrichment_sync")
def test_enrich_caches_duplicate_slug(mock_fetch):
    mock_fetch.return_value = ("a", "b", [{"aweme_id": "1"}])
    cards = [
        {"content_format": "haul"},
        {"format_name_vi": "Haul", "mechanism_vi": "unbox"},
    ]
    enrich_format_cards_from_corpus(cards, 3, analyzed_content_format=None)
    assert mock_fetch.call_count == 1


@patch("getviews_pipeline.pipelines.fetch_format_corpus_enrichment_sync")
def test_enrich_skips_multi_card_when_unresolvable(mock_fetch):
    cards = [
        {"format_name_vi": "ZZZ unknown", "view_range": "keep-me"},
        {"format_name_vi": "AAA mystery"},
    ]
    out = enrich_format_cards_from_corpus(cards, 2, analyzed_content_format="haul")
    mock_fetch.assert_not_called()
    assert out[0]["view_range"] == "keep-me"


@patch("getviews_pipeline.pipelines.fetch_format_corpus_enrichment_sync")
def test_single_card_falls_back_to_analyzed_format(mock_fetch):
    mock_fetch.return_value = ("v", "e", [])
    cards = [{"format_name_vi": "zzz"}]
    enrich_format_cards_from_corpus(cards, 5, analyzed_content_format="recipe")
    mock_fetch.assert_called_once()
    assert mock_fetch.call_args[0][0] == "recipe"
