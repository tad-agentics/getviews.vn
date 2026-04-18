"""Tests for hashtag_niche_map.score_niche_match (Phase 1 KOL finder)."""

from __future__ import annotations

from getviews_pipeline.hashtag_niche_map import score_niche_match


# Canned hashtag → niche map. Each test passes this explicitly so it doesn't
# touch the module-level cache.
_HMAP = {
    "skincare": 1,
    "lamdep": 1,
    "kbeauty": 1,
    "serum": 1,
    "fitness": 2,
    "gym": 2,
    "nauan": 3,
    "recipe": 3,
}
_GENERIC = frozenset({"fyp", "foryou", "viral", "trending"})


def _score(posts: list[list[str]], niche_id: int) -> float:
    return score_niche_match(posts, niche_id, hashtag_map=_HMAP, generic_set=_GENERIC)


def test_all_posts_in_target_niche() -> None:
    posts = [
        ["#skincare", "#serum"],
        ["#kbeauty"],
        ["#lamdep", "#skincare"],
    ]
    assert _score(posts, 1) == 1.0


def test_half_posts_in_target_niche() -> None:
    posts = [
        ["#skincare"],     # niche 1
        ["#fitness"],      # niche 2
        ["#serum"],        # niche 1
        ["#gym"],          # niche 2
    ]
    assert _score(posts, 1) == 0.5


def test_zero_match() -> None:
    posts = [["#fitness"], ["#gym"], ["#nauan"]]
    assert _score(posts, 1) == 0.0


def test_generic_only_posts_excluded_from_denominator() -> None:
    # A post with only #fyp isn't counted either way — it's unclassifiable,
    # not a miss.
    posts = [
        ["#skincare"],     # niche 1 ✓
        ["#fyp", "#viral"], # excluded from denominator
        ["#kbeauty"],      # niche 1 ✓
    ]
    assert _score(posts, 1) == 1.0


def test_unmapped_hashtags_count_as_miss() -> None:
    # If all hashtags are unknown (not generic, not in map), the post is still
    # counted in the denominator but produces no match — so it's a miss.
    posts = [
        ["#skincare"],
        ["#completelyunknowntag"],
    ]
    assert _score(posts, 1) == 0.5


def test_empty_input_returns_zero() -> None:
    assert _score([], 1) == 0.0


def test_all_generic_returns_zero() -> None:
    posts = [["#fyp"], ["#viral"]]
    assert _score(posts, 1) == 0.0


def test_tie_broken_by_first_max() -> None:
    # Post has 1 skincare tag + 1 fitness tag — max() picks whichever comes first.
    # The function doesn't guarantee which tier wins on a tie; test both outcomes.
    posts = [["#skincare", "#fitness"]]
    r1 = _score(posts, 1)
    r2 = _score(posts, 2)
    assert (r1 == 1.0 and r2 == 0.0) or (r1 == 0.0 and r2 == 1.0)
