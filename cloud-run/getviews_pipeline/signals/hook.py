from __future__ import annotations

from getviews_pipeline.signals.base import Evidence, Signal


def extract_hook_signals(ctx: dict) -> list[Signal]:
    ua = ctx.get("user_analysis") or {}
    ha = ua.get("hook_analysis") or {}
    if not isinstance(ha, dict):
        return []

    fft = str(ha.get("first_frame_type") or ha.get("opening_visual") or "").lower()
    hook_type = str(ha.get("hook_type") or "").lower()

    out: list[Signal] = []

    if fft and "product" not in fft and "face" not in fft:
        out.append(
            Signal(
                id="hook_first_frame_non_product",
                section_id="diagnosis",
                taxonomy_ref="§3",
                salience=0.74,
                claim="Khung mở đầu chưa lộ rõ sản phẩm / kết quả so với pattern review trong nhiều ngách.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote=f"first_frame_type={fft or hook_type}",
                        location="user_analysis.hook_analysis",
                    )
                ],
                suggested_fix="Cân nhắc close-up sản phẩm hoặc kết quả trong 0–2s.",
            )
        )

    layering = str(ha.get("hook_layering") or "").lower()
    if layering == "single":
        out.append(
            Signal(
                id="hook_layering_single",
                section_id="diagnosis",
                taxonomy_ref="§3",
                salience=0.62,
                claim="Hook đơn lớp — thiếu xếp chồng hình + chữ + âm thanh.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote="hook_layering=single",
                        location="user_analysis.hook_analysis",
                    )
                ],
                suggested_fix="Thêm text overlay hoặc lớp âm thanh hỗ trợ hook trong 0–3s.",
            )
        )

    if ha.get("hook_body_contract") is False:
        out.append(
            Signal(
                id="hook_body_contract_violated",
                section_id="diagnosis",
                taxonomy_ref="§3",
                salience=0.88,
                claim="Thân video không trả lời lời hứa hook — rủi ro rớt retention giữa chừng.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote="hook_body_contract=false",
                        location="user_analysis.hook_analysis",
                    )
                ],
                suggested_fix="Đồng bộ beat đầu với payoff giây 4–12.",
            )
        )

    return out
