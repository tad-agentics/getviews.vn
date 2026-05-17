/**
 * Vietnamese hook name mapping — aligns with cloud-run `HookType` + enum_labels_vi.
 *
 * Usage: HOOK_NAMES_VI[hook_type] → display label in Vietnamese
 * Fallback: unknown types fall back to title-cased hook_type.
 */
export const HOOK_NAMES_VI: Record<string, string> = {
  bold_claim:        "Tuyên Bố Táo Bạo",
  challenge:         "Thử Thách",
  curiosity_gap:     "Tạo Khoảng Trống Tò Mò",
  controversy:       "Gây Tranh Cãi",
  shock_stat:        "Số Liệu Gây Sốc",
  how_to:            "Hướng Dẫn Thực Hành",
  tips_value:        "Tips / Giá Trị Nhanh",
  warning:           "Cảnh Báo",
  question:          "Đặt Câu Hỏi",
  social_proof:      "Chứng Minh Xã Hội",
  pain_point:        "Chạm Nỗi Đau",
  trend_hijack:      "Bắt Trend",
  fomo_urgency:      "FOMO / Gấp",
  reaction:          "Phản Ứng",
  comparison:        "So Sánh",
  expose:            "Bóc Phốt",
  vach_tran:         "Vạch Trần",
  dialect_identity:  "Giọng Miền",
  story:             "Mở Đầu Bằng Câu Chuyện",
  story_open:        "Mở Đầu Bằng Câu Chuyện",
  pov:               "POV",
  transformation:    "Trước & Sau",
  listicle:          "Danh Sách",
  product_reveal:    "Hé Lộ Sản Phẩm",
  price_shock:       "Giá Sốc",
  gia_soc:           "Giá Sốc",
  insider:           "Bí Mật / Nội Bộ",
  secret:            "Bí Mật / Nội Bộ",
};

/** Resolve a hook_type key to its Vietnamese display name. */
export function hookNameVI(hookType: string): string {
  return (
    HOOK_NAMES_VI[hookType] ??
    hookType
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  );
}
