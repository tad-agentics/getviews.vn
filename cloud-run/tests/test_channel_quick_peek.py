"""W5-4 — channel quick peek teaser selection."""

from __future__ import annotations

from getviews_pipeline.channel_findings import ChannelFinding, pick_channel_quick_peek


def test_pick_channel_quick_peek_prefers_ceiling() -> None:
    findings = [
        ChannelFinding(
            id="channel_format_entropy_high",
            taxonomy_ref="§2.2",
            strength="medium",
            claim="entropy teaser",
            evidence=["x"],
            section_hint="what_falling",
            salience=0.78,
        ),
        ChannelFinding(
            id="channel_view_ceiling_300",
            taxonomy_ref="§2.1",
            strength="high",
            claim="ceiling teaser",
            evidence=["y"],
            section_hint="verdict",
            salience=0.92,
        ),
    ]
    peek = pick_channel_quick_peek(findings)
    assert peek is not None
    assert peek["finding_id"] == "channel_format_entropy_high"
    assert "entropy" in peek["teaser"]
