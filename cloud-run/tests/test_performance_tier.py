from getviews_pipeline.pipelines import classify_performance_tier_corpus, refine_performance_tier


def test_corpus_hit():
    assert classify_performance_tier_corpus(200000, 80000) == "hit"


def test_corpus_flop():
    assert classify_performance_tier_corpus(231, 2400) == "flop"


def test_corpus_average():
    assert classify_performance_tier_corpus(2000, 2400) == "average"


def test_corpus_unknown():
    assert classify_performance_tier_corpus(1000, None) == "unknown"


def test_account_refine_agreement():
    ctx = {"available": True, "median_views": 500}
    assert refine_performance_tier("flop", 100, ctx) == "flop"


def test_account_refine_collapse():
    ctx = {"available": True, "median_views": 50}
    assert refine_performance_tier("flop", 100, ctx) == "average"


def test_account_overrides_corpus_directionally():
    ctx = {"available": True, "median_views": 10000}
    assert refine_performance_tier("hit", 200000, ctx) == "hit"


# ── 2026-06-11 — age guard: low views on a fresh video are not a verdict ──


def test_corpus_early_when_fresh_and_low():
    assert classify_performance_tier_corpus(231, 2400, video_age_days=1.2) == "early"


def test_corpus_fresh_average_ratio_is_early():
    # Even mid-band ratios are inconclusive while views accumulate.
    assert classify_performance_tier_corpus(2000, 2400, video_age_days=2.9) == "early"


def test_corpus_fresh_hit_is_conclusive():
    # Views only go up — a ≥2× ratio is a hit even on day 1.
    assert classify_performance_tier_corpus(200000, 80000, video_age_days=0.5) == "hit"


def test_corpus_age_guard_off_at_three_days():
    assert classify_performance_tier_corpus(231, 2400, video_age_days=3.0) == "flop"


def test_corpus_no_age_keeps_legacy_behavior():
    assert classify_performance_tier_corpus(231, 2400) == "flop"
    assert classify_performance_tier_corpus(2000, 2400) == "average"


def test_refine_early_upgrades_only_on_channel_breakout():
    ctx = {"available": True, "median_views": 100}
    # 5× the channel median — conclusive breakout even while early.
    assert refine_performance_tier("early", 500, ctx) == "hit"
    # Low account ratio is just as unfinished — stays early, never flop.
    assert refine_performance_tier("early", 30, ctx) == "early"


def test_refine_early_unavailable_channel_stays_early():
    assert refine_performance_tier("early", 30, {"available": False}) == "early"
