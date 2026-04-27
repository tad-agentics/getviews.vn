import { memo } from "react";
import { useNavigate } from "react-router";
import { Archive, ArrowRight } from "lucide-react";

import { useDouyinFeed } from "@/hooks/useDouyinFeed";
import { useDouyinPatterns } from "@/hooks/useDouyinPatterns";

/**
 * Trends — compact Kho Douyin link card (PR-T5).
 *
 * Mirrors the design pack's pre-VN-signal card (``screens/trends.jsx``
 * lines 351-384): full-width clickable button between the §0 hero and
 * §I PATTERN grid. Click navigates to the Kho Douyin surface
 * (``/app/douyin``) where translated/curated TQ patterns live.
 *
 * Layout: small ink-bg square avatar with a coral archive icon on the
 * left, three text rows (mono uc kicker, bold mid-line, mono caption)
 * to its right, ``→`` chevron on the far right. Border darkens on
 * hover and the card lifts 1px.
 *
 * D7 (2026-06-06) — pulls live counts from ``useDouyinPatterns`` +
 * ``useDouyinFeed`` so the mid-line reads "N pattern đang nổ ở TQ ·
 * M video đã sub VN" with real numbers (design pack line 376).
 * Falls back to count-less copy when either hook is still pending /
 * empty so the card always renders something useful.
 *
 * Both hooks are already mounted by ``DouyinScreen``; calling them
 * here adds zero round-trips because TanStack dedupes by queryKey.
 */

export const TrendsDouyinCard = memo(function TrendsDouyinCard() {
  const navigate = useNavigate();
  const { data: feed } = useDouyinFeed();
  const { data: patternsData } = useDouyinPatterns();

  const videoCount = feed?.videos.length ?? 0;
  const patternCount = patternsData?.patterns.length ?? 0;
  // Show concrete counts when both are non-zero; otherwise drop to
  // the count-less fallback so the card stays meaningful pre-cron.
  const headlineLine =
    patternCount > 0 && videoCount > 0
      ? `${patternCount} pattern đang nổ ở TQ · ${videoCount} video đã sub VN`
      : "Pattern đang nổ ở TQ · video đã sub VN";

  return (
    <button
      type="button"
      onClick={() => navigate("/app/douyin")}
      aria-label="Mở Kho Douyin — tín hiệu sớm từ Trung Quốc"
      className="group mb-9 flex w-full items-center justify-between gap-4 rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-[18px] py-3.5 text-left text-[13px] text-[color:var(--gv-ink-2)] transition-[border-color,transform] duration-150 hover:-translate-y-px hover:border-[color:var(--gv-ink)]"
    >
      <span className="flex min-w-0 items-center gap-3.5">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[color:var(--gv-ink)] text-[color:var(--gv-accent)]"
          aria-hidden
        >
          <Archive className="h-4 w-4" strokeWidth={1.7} />
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="gv-mono mb-[3px] text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-accent-deep)]">
            <span aria-hidden>🇨🇳</span> TÍN HIỆU SỚM · DOUYIN → VN
          </span>
          <span className="text-[14px] font-semibold leading-[1.25] text-[color:var(--gv-ink)]">
            {headlineLine}
          </span>
          <span className="gv-mono mt-0.5 text-[10.5px] text-[color:var(--gv-ink-4)]">
            Đi trước VN 4–10 tuần · không cần VPN
          </span>
        </span>
      </span>
      <ArrowRight
        className="h-4 w-4 shrink-0 text-[color:var(--gv-ink-3)] transition-transform group-hover:translate-x-0.5"
        strokeWidth={1.7}
        aria-hidden
      />
    </button>
  );
});
