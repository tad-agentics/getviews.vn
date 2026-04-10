/**
 * Vietnamese hook name mapping — 12 hook types used in TikTok Vietnam corpus.
 * Mirrors the hook taxonomy in cloud-run/getviews_pipeline/knowledge_base.py.
 *
 * Usage: HOOK_NAMES_VI[hook_type] → display label in Vietnamese
 * Fallback: unknown types fall back to title-cased hook_type.
 */
export const HOOK_NAMES_VI: Record<string, string> = {
  bold_claim:      "Tuyên Bố Táo Bạo",
  curiosity_gap:   "Tạo Khoảng Trống Tò Mò",
  controversy:     "Gây Tranh Cãi",
  shock_stat:      "Số Liệu Gây Sốc",
  how_to:          "Hướng Dẫn Thực Hành",
  warning:         "Cảnh Báo",
  question:        "Đặt Câu Hỏi",
  social_proof:    "Chứng Minh Xã Hội",
  story:           "Mở Đầu Bằng Câu Chuyện",
  transformation:  "Trước & Sau",
  listicle:        "Danh Sách",
  product_reveal:  "Hé Lộ Sản Phẩm",
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
