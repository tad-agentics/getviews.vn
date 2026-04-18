import { memo } from "react";
import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { useTopBreakouts, type BreakoutVideo } from "@/hooks/useTopBreakouts";

/**
 * BreakoutGrid — 3 breakout tiles (9:16 aspect). Matches the design's
 * bottom-of-home breakout row. Hook phrase renders in serif-italic,
 * multiplier as a pink BREAKOUT sticker in the top-left.
 */

function formatViews(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return m >= 10 ? `${Math.round(m)}M` : `${m.toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toString();
}

export const BreakoutGrid = memo(function BreakoutGrid({
  nicheId,
}: {
  nicheId: number | null;
}) {
  const { data: videos, isPending } = useTopBreakouts(nicheId, 3);

  if (isPending) {
    return (
      <section>
        <SectionHeader kicker="BIÊN TẬP CHỌN" title="3 video đột phá" caption="View vượt 10× so với trung bình kênh trong 48 giờ qua." />
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="aspect-[9/12] animate-pulse rounded-[12px] bg-[color:var(--gv-canvas-2)]" />
          ))}
        </div>
      </section>
    );
  }

  if (!videos || videos.length === 0) {
    return null; // no breakouts this week — skip the whole section quietly
  }

  return (
    <section>
      <SectionHeader
        kicker="BIÊN TẬP CHỌN"
        title="3 video đột phá"
        caption="View vượt 10× so với trung bình kênh trong 48 giờ qua."
        right={
          <Link
            to="/app/trends"
            className="inline-flex items-center gap-1.5 rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[color:var(--gv-ink-3)] transition-colors hover:border-[color:var(--gv-rule)] hover:text-[color:var(--gv-ink)]"
          >
            Xem tất cả
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        }
      />
      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
        {videos.map((v: BreakoutVideo) => (
          <a
            key={v.video_id}
            href={v.tiktok_url}
            target="_blank"
            rel="noreferrer"
            className="group block overflow-hidden rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-ink)] transition-transform hover:-translate-y-0.5"
          >
            <div className="relative aspect-[9/12] w-full overflow-hidden">
              {v.thumbnail_url ? (
                <img
                  src={v.thumbnail_url}
                  alt=""
                  loading="lazy"
                  className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                />
              ) : (
                <div className="h-full w-full bg-[color:var(--gv-ink-2)]" />
              )}
              {v.breakout_multiplier != null ? (
                <span className="absolute left-2 top-2 inline-flex items-center gap-1 rounded-full bg-[color:var(--gv-accent)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white">
                  {v.breakout_multiplier.toFixed(1)}× BREAKOUT
                </span>
              ) : null}
              <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent p-3 text-white">
                {v.hook_phrase ? (
                  <p className="gv-serif-italic line-clamp-2 text-sm leading-snug">
                    “{v.hook_phrase}”
                  </p>
                ) : null}
                <p className="mt-1 text-[11px] uppercase tracking-wider text-white/70 gv-mono">
                  @{v.creator_handle} · {formatViews(v.views)} views
                </p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
});
