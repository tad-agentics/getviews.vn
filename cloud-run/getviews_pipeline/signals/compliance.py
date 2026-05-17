from __future__ import annotations

from getviews_pipeline.signals.base import Evidence, Signal


def extract_compliance_signals(ctx: dict) -> list[Signal]:
    flags = ctx.get("compliance_flags") or []
    if not flags:
        return []
    first = flags[0] if isinstance(flags[0], dict) else {}
    phrase = str(first.get("phrase") or first.get("text") or "restricted content")
    return [
        Signal(
            id="compliance_hit",
            section_id="compliance",
            taxonomy_ref="§10",
            salience=1.0,
            claim=f"Phát hiện cụm từ rủi ro tuân thủ: {phrase[:80]}",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=phrase[:200],
                    location=str(first.get("location") or "compliance_flags[0]"),
                )
            ],
            suggested_fix="Viết lại theo Khung an toàn quảng cáo và chú thích #qc / voice khi có quan hệ thương mại.",
        )
    ]
