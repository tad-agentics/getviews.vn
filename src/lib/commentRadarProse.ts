import type { CommentRadarData } from "@/lib/types/corpus-sidecars";

/** Deterministic Vietnamese commentary for the metadata block comment radar. */
export function buildCommentRadarProse(data: CommentRadarData | null | undefined): string {
  if (!data || data.sampled <= 0) return "";

  const pos = Math.max(0, Math.min(100, data.sentiment.positive_pct));
  const neg = Math.max(0, Math.min(100, data.sentiment.negative_pct));
  const neu = Math.max(0, 100 - pos - neg);
  const purchase = data.purchase_intent.count;
  const questions = data.questions_asked;
  const parts: string[] = [];

  if (neg >= 25) {
    parts.push(
      `${neg.toFixed(0)}% bình luận tiêu cực trong mẫu — đọc các comment chê trước khi quay tiếp để tránh lặp lỗi hook, sản phẩm hoặc giọng.`,
    );
  } else if (pos >= 40) {
    parts.push(
      `${pos.toFixed(0)}% bình luận tích cực — khán giả phản hồi tốt với nội dung; giữ format và giọng này cho clip kế tiếp.`,
    );
  } else if (neu >= 85) {
    parts.push(
      `Bình luận chủ yếu trung tính (${neu.toFixed(0)}%) — người xem chưa bộc lộ cảm xúc rõ; thử chốt bằng câu hỏi hoặc CTA cụ thể ở caption.`,
    );
  } else {
    parts.push(
      `Cảm xúc bình luận cân bằng (${pos.toFixed(0)}% tích cực · ${neu.toFixed(0)}% trung tính · ${neg.toFixed(0)}% tiêu cực) — chưa có cực đoan mạnh trong mẫu.`,
    );
  }

  if (purchase >= 3) {
    parts.push(
      `${purchase} bình luận thể hiện ý định mua — tín hiệu conversion mạnh cho affiliate hoặc brand deal; nhân đôi CTA «mua ở đâu» trong caption và pin link shop.`,
    );
  } else if (purchase > 0) {
    parts.push(
      `Có ${purchase} bình luận hỏi mua — tín hiệu conversion nhẹ; thêm link shop rõ trong caption để không bỏ lỡ đơn.`,
    );
  }

  if (questions >= 5) {
    parts.push(
      `${questions} câu hỏi trong mẫu — khán giả đang tìm thêm thông tin; trả lời pin hoặc làm follow-up trả lời trực tiếp.`,
    );
  } else if (questions > 0) {
    parts.push(
      `${questions} câu hỏi trong mẫu — cơ hội tăng tương tác bằng cách trả lời sớm ở comment pin.`,
    );
  }

  return parts.join(" ");
}

export function hasCommentRadarContent(
  data: CommentRadarData | null | undefined,
): data is CommentRadarData {
  return data != null && data.sampled > 0;
}
