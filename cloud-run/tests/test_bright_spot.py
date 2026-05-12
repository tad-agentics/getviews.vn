from getviews_pipeline.pipelines import compute_bright_spot_signal


def test_hook_only_problem():
    result = compute_bright_spot_signal(er_percentile_rank=85, views_vs_avg_ratio=0.3)
    assert result is not None
    assert result["signal_type"] == "hook_only_problem"


def test_performing_well():
    result = compute_bright_spot_signal(er_percentile_rank=80, views_vs_avg_ratio=2.5)
    assert result is not None
    assert result["signal_type"] == "performing_well"


def test_zero_format_avg_returns_none():
    result = compute_bright_spot_signal(er_percentile_rank=70, views_vs_avg_ratio=None)
    assert result is None


def test_content_and_hook():
    result = compute_bright_spot_signal(er_percentile_rank=20, views_vs_avg_ratio=0.2)
    assert result is not None
    assert result["signal_type"] == "content_and_hook"


def test_thin_corpus_high_er():
    result = compute_bright_spot_signal(er_percentile_rank=90, views_vs_avg_ratio=None)
    assert result is None
