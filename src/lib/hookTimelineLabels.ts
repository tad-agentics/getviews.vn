import type { HookTimelineEventType } from "@/lib/api-types";

/** Mirrors ``HOOK_TIMELINE_EVENT_VI`` in ``cloud-run/getviews_pipeline/enum_labels_vi.py``. */
export const HOOK_TIMELINE_EVENT_VI: Record<HookTimelineEventType, string> = {
  face_enter: "Khuôn mặt xuất hiện",
  first_word: "Lời thoại đầu",
  text_overlay: "Chữ hiện lên màn hình",
  sound_drop: "Nhạc/âm thanh bắt đầu",
  cut: "Cắt cảnh đầu tiên",
  product_enter: "Sản phẩm xuất hiện",
  reveal: "Khoảnh khắc chốt hạ",
};
