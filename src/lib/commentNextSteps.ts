import type { CommentRadarData } from "@/lib/types/corpus-sidecars";

/** Bullet for next-steps when comment radar shows recurring purchase/question intent. */
export function buildCommentNextStepBullet(data: CommentRadarData | null | undefined): string | null {
  if (!data || data.sampled <= 0) return null;

  const phrases = data.purchase_intent?.top_phrases?.filter(Boolean) ?? [];
  if (phrases.length >= 2) {
    return `Khán giả hỏi lặp «${phrases[0]}» / «${phrases[1]}» — làm video tiếp trả lời trực tiếp hoặc pin comment với link shop.`;
  }
  if (phrases.length === 1) {
    return `Khán giả hỏi lặp «${phrases[0]}» — làm follow-up trả lời câu hỏi này ở video sau.`;
  }
  if (data.questions_asked >= 5) {
    return `${data.questions_asked} câu hỏi trong comment — chọn 1 câu hỏi hay nhất làm chủ đề video tiếp theo.`;
  }
  if (data.purchase_intent.count >= 3) {
    return `${data.purchase_intent.count} comment thể hiện ý mua — video tiếp nên demo sản phẩm + link shop rõ trong caption.`;
  }
  return null;
}
