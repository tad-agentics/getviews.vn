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
