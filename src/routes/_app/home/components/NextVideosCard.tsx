import { memo } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, Calendar } from "lucide-react";

import { logUsage } from "@/lib/logUsage";

/**
 * NextVideosCard — Home screen entry point for the Ideas "5 video tiếp theo"
 * report. Deep-links to /app/answer with a niche-pre-filled query so the
 * creator lands directly on the content-calendar layout Wave 2 PR #4
 * shipped.
 *
 * Mirrors the creator survey's #1 "rất hữu ích" finding: 82% endorsed
 * the "5 next videos with hook" framing. This card is the home-screen
 * path to that report — one tap to the answer.
 *
 * Graceful degradation: when the creator hasn't set a primary niche,
 * the card still renders with the default query "5 video tiếp theo
 * tôi nên làm?" and lets the Answer screen resolve the niche via its
 * tier-1 router.
 */

interface Props {
  nicheLabel: string | null;
  /** Bỏ `<section>` bọc ngoài — dùng trong tier 01 “GỢI Ý HÔM NAY”. */
  embedded?: boolean;
}

export const NextVideosCard = memo(function NextVideosCard({ nicheLabel, embedded = false }: Props) {
  const navigate = useNavigate();

  const hasNiche = Boolean(nicheLabel && nicheLabel.trim());
  const query = hasNiche
    ? `5 video tiếp theo tôi nên làm trong ngách ${nicheLabel}?`
    : "5 video tiếp theo tôi nên làm?";

  const onClick = () => {
    logUsage("home_next_videos_card", { has_niche: hasNiche });
    navigate(`/app/answer?q=${encodeURIComponent(query)}`);
  };

  const button = (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-start gap-4 rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-[22px] text-left transition-colors hover:bg-[color:var(--gv-canvas-2)] min-[900px]:items-center"
      aria-label="Mở báo cáo 5 video tiếp theo bạn nên làm"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[6px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)]">
        <Calendar className="h-5 w-5 text-[color:var(--gv-ink-2)]" strokeWidth={1.7} />
      </div>

      <div className="min-w-0 flex-1">
        <p className="gv-kicker gv-kicker--dot mb-1 text-[color:var(--gv-accent-deep)]">
          Lịch quay tuần này
        </p>
        <h3 className="gv-tight text-[20px] text-[color:var(--gv-ink)] min-[900px]:text-[22px]">
          {hasNiche ? `5 video tiếp theo — ${nicheLabel}` : "5 video tiếp theo bạn nên làm"}
        </h3>
        <p className="mt-1 text-[13px] leading-[1.5] text-[color:var(--gv-ink-3)]">
          Dựa trên 7 ngày gần nhất — hook, câu mở, góc nội dung cụ thể cho từng video.
        </p>
      </div>

      <div className="hidden shrink-0 items-center gap-2 text-[13px] text-[color:var(--gv-ink-2)] min-[900px]:flex">
        <span className="gv-mono uppercase tracking-wide">Mở báo cáo</span>
        <ArrowRight className="h-4 w-4" strokeWidth={1.7} />
      </div>
    </button>
  );

  if (embedded) return button;

  return <section>{button}</section>;
});
