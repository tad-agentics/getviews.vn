"""§2 Context signals (tương tác chéo) — no clock-time posting ratings (redesign 2026-05)."""

from __future__ import annotations

from getviews_pipeline.signals.base import Evidence, Signal


def _cheo_detail(weak_watch: bool, weak_reach: bool) -> str:
    parts: list[str] = []
    if weak_watch:
        parts.append("giữ chân cuối clip thấp")
    if weak_reach:
        parts.append("reach so với trung bình ngách yếu")
    return " và ".join(parts) if parts else "watch/reach lệch baseline"


def extract_tuong_tac_cheo_signal(ctx: dict) -> list[Signal]:
    """Heuristic: ER cực cao vs median ngách nhưng giữ chân/ reach yếu — nghi nhóm chéo."""
    st = ctx.get("user_stats") if isinstance(ctx.get("user_stats"), dict) else {}
    nm = ctx.get("niche_meta") if isinstance(ctx.get("niche_meta"), dict) else {}
    er = float(st.get("engagement_rate") or 0.0)
    med = float(nm.get("median_er") or nm.get("avg_engagement_rate") or 0.0)
    if med <= 0:
        return []
    if er < 5.0 * med:
        return []
    ret_raw = st.get("retention_end_pct")
    vvr_raw = st.get("views_vs_avg_ratio")
    weak_watch = False
    if ret_raw is not None:
        try:
            weak_watch = float(ret_raw) < 50.0
        except (TypeError, ValueError):
            pass
    weak_reach = False
    if vvr_raw is not None:
        try:
            weak_reach = float(vvr_raw) < 0.9
        except (TypeError, ValueError):
            pass
    if not weak_watch and not weak_reach:
        return []
    return [
        Signal(
            id="context_tuong_tac_cheo_heuristic",
            section_id="diagnosis",
            taxonomy_ref="§2",
            salience=0.7,
            claim=(
                f"ER mặt nổi {er:.2f}% gấp ≥5× median ngách (~{med:.2f}%) nhưng "
                f"{_cheo_detail(weak_watch, weak_reach)} "
                f"— nghi giao lưu tương tác / tín hiệu không organic."
            ),
            evidence=[
                Evidence(
                    type="niche_norms_pct",
                    quote=f"er={er}% median_er={med}% retention_end={ret_raw} v_v_avg={vvr_raw}",
                    location="user_stats+niche_meta",
                )
            ],
            suggested_fix=(
                "Giảm seed nhóm chéo; ưu tiên watch-time và share tự nhiên; "
                "đối chiếu Nguồn trong TikTok Studio."
            ),
        )
    ]


def extract_context_signals(ctx: dict) -> list[Signal]:
    return extract_tuong_tac_cheo_signal(ctx)
