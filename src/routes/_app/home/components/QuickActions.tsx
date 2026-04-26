import { memo, useCallback } from "react";
import { useNavigate } from "react-router";
import { Clapperboard, Eye, TrendingUp, FileText, Sparkles } from "lucide-react";

/**
 * Sáu lối tắt chính — ref: viền ink, chữ đậm, icon đen (khác hàng gợi ý Sparkles đỏ).
 */

const PRIMARY =
  "inline-flex min-h-[44px] max-w-full items-center gap-2 rounded-full border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-left text-xs font-bold leading-snug text-[color:var(--gv-ink)] transition-colors hover:bg-[color:var(--gv-canvas-2)]";

const ICO = "h-3.5 w-3.5 shrink-0 text-[color:var(--gv-ink)]";

export type QuickActionsProps = {
  nicheLabel: string;
  onAnswerPrompt: (text: string) => void;
  onPrefillComposer: (text: string) => void;
};

export const QuickActions = memo(function QuickActions({
  nicheLabel,
  onAnswerPrompt,
  onPrefillComposer,
}: QuickActionsProps) {
  const navigate = useNavigate();

  const channelPrefill = useCallback(() => {
    onPrefillComposer("Soi kênh đối thủ — dán @handle TikTok vào đây:\n");
  }, [onPrefillComposer]);

  return (
    <>
      <button type="button" onClick={() => navigate("/app/video")} className={PRIMARY}>
        <Clapperboard className={ICO} strokeWidth={2} aria-hidden />
        <span className="min-w-0">Soi video</span>
      </button>
      <button type="button" onClick={channelPrefill} className={PRIMARY}>
        <Eye className={ICO} strokeWidth={2} aria-hidden />
        <span className="min-w-0">Soi kênh đối thủ</span>
      </button>
      <button type="button" onClick={() => navigate("/app/trends")} className={PRIMARY}>
        <TrendingUp className={ICO} strokeWidth={2} aria-hidden />
        <span className="min-w-0">Xu hướng tuần này</span>
      </button>
      <button type="button" onClick={() => navigate("/app/script")} className={PRIMARY}>
        <FileText className={ICO} strokeWidth={2} aria-hidden />
        <span className="min-w-0">Lên kịch bản quay</span>
      </button>
      <button
        type="button"
        onClick={() =>
          onAnswerPrompt(
            `Tư vấn nhanh: nên làm chủ đề gì tuần này trong ngách ${nicheLabel}, dựa trên trend hiện tại?`,
          )
        }
        className={PRIMARY}
      >
        <Sparkles className={ICO} strokeWidth={2} aria-hidden />
        <span className="min-w-0">Tư vấn content</span>
      </button>
    </>
  );
});
