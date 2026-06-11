import { memo, useCallback, useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";

import { CarouselBadge } from "@/components/CarouselBadge";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import type { PatternVideo, TopPattern } from "@/hooks/useTopPatterns";
import { formatViews } from "@/lib/formatters";
import { logUsage } from "@/lib/logUsage";
import { ChannelQuickPeekTeaser } from "./components/ChannelQuickPeekTeaser";

/**
 * Trends — § I PatternCard.
 *
 * L2.2 Sprint 5 reshape — the card surfaces the *formula* (Gemini-extracted
 * recipe), not the bucket name. A creator scanning the section asks
 * "công thức nào đang được video viral trong ngách dùng?" — so the card
 * answers with:
 *
 *   • Headline = ``structure[0]`` (the Hook line of the recipe), not the
 *     ``display_name`` (which is a 7-attribute taxonomy bucket label and
 *     reads like an analyst category).
 *   • Sub = ``why`` (psychology + algorithm signal) when the deck synth
 *     has produced one; falls back to the top-views ``sample_hook``.
 *   • Stats = ``↑ {lift}× ngách · {niche_video_count} video trong ngách`` —
 *     within-niche credibility, never the cross-niche ``instance_count``.
 *   • Videos = flex row of however-many real videos exist (1-4). Empty
 *     placeholder cells were removed because at small ``niche_video_count``
 *     they made cards look broken.
 *   • CTA = "HỌC CÔNG THỨC →" — verb, not noun. The click opens the
 *     existing ``PatternModal`` which still owns the deep-teach surface.
 *
 * Card body is intentionally lean — its job is to help the creator
 * *decide which deck to open*, not to teach the recipe inline.
 */

export const PatternCard = memo(function PatternCard({
  pattern,
  onOpen,
}: {
  pattern: TopPattern;
  onOpen?: (pattern: TopPattern) => void;
}) {
  const headline = pickHeadline(pattern);
  const sub = pickSub(pattern);
  const liftLabel = formatLift(pattern.lift_vs_niche);
  const peekHandle = pattern.videos[0]?.creator_handle ?? null;

  return (
    <article className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] transition-transform duration-150 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_rgba(0,0,0,0.18)]">
      <button
        type="button"
        onClick={() => {
          // L2.2 measurement — pairs with daily_ritual_script_clicked /
          // daily_ritual_evidence_expanded so the admin funnel can
          // attribute deck opens to the Trends discovery surface.
          logUsage("pattern_card_clicked", {
            pattern_id: pattern.id,
            niche_video_count: pattern.niche_video_count,
            lift_vs_niche: pattern.lift_vs_niche,
          });
          onOpen?.(pattern);
        }}
        className="group flex h-full w-full flex-col text-left"
        aria-label={`Mở công thức: ${headline}`}
      >
        {/* Video strip — 1-4 actual videos, no padded placeholders. */}
        <CollageStrip videos={pattern.videos} pool={pattern.video_pool} />

        {/* Body */}
        <div className="flex flex-col gap-2.5 px-3.5 py-3.5">
          <div className="min-w-0">
            <h3 className="gv-tight m-0 text-sm font-semibold leading-[1.25] tracking-[-0.01em] text-[color:var(--gv-ink)] line-clamp-3">
              {headline}
            </h3>
            {sub ? (
              <p className="mt-1.5 text-[12px] leading-[1.45] text-[color:var(--gv-ink-3)] line-clamp-2">
                {sub}
              </p>
            ) : null}
            <ChannelQuickPeekTeaser handle={peekHandle} />
          </div>

          {/* Stat strip — tier-aware (Sprint 7b).
              "strong" tier (n≥3 + lift≥1.2×) → green ↑ {lift}× ngách badge.
              "early" tier (n≥1 + lift≥1.5×) → yellow "Tín hiệu sớm" badge so
              creators don't read small-sample observations as the strict
              "đang chạy tốt" claim. */}
          <div className="flex items-center gap-2 border-t border-[color:var(--gv-rule)] pt-2">
            {pattern.tier === "strong" && liftLabel ? (
              <span
                className="gv-mono inline-flex items-center whitespace-nowrap rounded-[2px] px-1.5 py-0.5 text-[11px] font-bold gv-kicker tracking-[0.06em]"
                style={{
                  background: "color-mix(in srgb, var(--gv-pos) 14%, transparent)",
                  color: "var(--gv-pos-deep)",
                }}
                title="Lượt xem trung bình của công thức này so với mức trung bình của ngách trong 30 ngày qua"
              >
                ↑ {liftLabel} ngách
              </span>
            ) : pattern.tier === "early" ? (
              <span
                className="gv-mono inline-flex items-center whitespace-nowrap rounded-[2px] px-1.5 py-0.5 text-[11px] font-bold gv-kicker tracking-[0.06em]"
                style={{
                  background: "color-mix(in srgb, var(--gv-warn,#d49a3b) 18%, transparent)",
                  color: "var(--gv-warn-deep,#7a4a00)",
                }}
                title={`Tín hiệu sớm — chỉ có ${pattern.niche_video_count} video thực tế trong ngách sử dụng, hiệu số lượt xem ${liftLabel ?? '—'}`}
              >
                Tín hiệu sớm{liftLabel ? ` · ↑${liftLabel}` : ""}
              </span>
            ) : null}
            <span className="gv-kicker text-[color:var(--gv-ink-3)] truncate">
              {pattern.niche_video_count} video trong ngách
            </span>
          </div>

          {/* CTA — verb, opens the deep-teach modal. */}
          <span className="gv-mono inline-flex items-center gap-1 self-start text-[11px] font-bold gv-kicker tracking-[0.1em] text-[color:var(--gv-accent)] group-hover:translate-x-0.5 transition-transform">
            HỌC CÔNG THỨC
            <ArrowRight className="h-3 w-3" strokeWidth={2.4} aria-hidden />
          </span>
        </div>
      </button>
    </article>
  );
});

/**
 * Prefer the first line of the synthesized recipe (the Hook). Strip a
 * leading "Mở:" / "Hook:" tag if present so the card reads cleanly.
 * Falls back to ``display_name`` only if no recipe — but the hook
 * already filters those out, so the fallback is purely defensive.
 */
function pickHeadline(pattern: TopPattern): string {
  const first = pattern.structure?.[0]?.trim();
  if (first) return first.replace(/^(?:Mở|Hook)\s*[:：]\s*/i, "");
  return pattern.display_name;
}

/**
 * "Why it works" reads cleaner than the raw hook quote — show that
 * when the deck synth produced one. Otherwise the most-viewed
 * ``sample_hook`` (kept in italics so creators can tell it's an actual
 * line a creator used).
 */
function pickSub(pattern: TopPattern): string | null {
  if (pattern.why?.trim()) return pattern.why.trim();
  if (pattern.sample_hook?.trim()) return `"${pattern.sample_hook.trim()}"`;
  return null;
}

/** Format the lift number — 1.85× rounded to 1 decimal, 3+ as integer. */
function formatLift(lift: number | null): string | null {
  if (lift == null || !Number.isFinite(lift) || lift <= 0) return null;
  if (lift >= 3) return `${Math.round(lift)}×`;
  return `${lift.toFixed(1)}×`;
}

/**
 * Render 1-4 videos as a horizontal strip. We deliberately don't pad
 * with empty cells — at small ``niche_video_count`` the placeholder
 * tiles dominated the card visually and read as "broken".
 */
function CollageStrip({
  videos,
  pool,
}: {
  videos: ReadonlyArray<PatternVideo>;
  pool: ReadonlyArray<PatternVideo>;
}) {
  const [cells, setCells] = useState(() => videos.slice(0, 4));

  useEffect(() => {
    setCells(videos.slice(0, 4));
  }, [videos]);

  const handleTileFailed = useCallback(
    (videoId: string) => {
      setCells((prev) => {
        const shown = new Set(prev.map((cell) => cell.video_id));
        const replacement = pool.find(
          (row) => row.video_id !== videoId && !shown.has(row.video_id),
        );
        if (!replacement) {
          const next = prev.filter((cell) => cell.video_id !== videoId);
          return next.length > 0 ? next : prev;
        }
        return prev.map((cell) => (cell.video_id === videoId ? replacement : cell));
      });
    },
    [pool],
  );

  if (cells.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-[color:var(--gv-canvas-2)] text-[11px] text-[color:var(--gv-ink-4)]"
        style={{ aspectRatio: "16 / 10" }}
        aria-hidden
      >
        Chưa có video mẫu
      </div>
    );
  }
  return (
    <div
      className="flex gap-px bg-[color:var(--gv-rule)]"
      style={{ aspectRatio: "16 / 10" }}
      aria-hidden
    >
      {cells.map((cell, i) => (
        <CollageTile
          key={cell.video_id || i}
          cell={cell}
          onThumbFailed={() => handleTileFailed(cell.video_id)}
        />
      ))}
    </div>
  );
}

function CollageTile({
  cell,
  onThumbFailed,
}: {
  cell: PatternVideo;
  onThumbFailed: () => void;
}) {
  const handleLabel = (cell.creator_handle ?? "").startsWith("@")
    ? cell.creator_handle
    : cell.creator_handle
      ? `@${cell.creator_handle}`
      : null;
  return (
    <div className="relative flex-1 overflow-hidden bg-[color:var(--gv-canvas-2)]">
      <VideoThumbnail
        thumbnailUrl={cell.thumbnail_url}
        videoId={cell.video_id}
        className="absolute inset-0 h-full w-full"
        placeholderClassName="bg-[color:var(--gv-canvas-2)]"
        onAllCandidatesFailed={onThumbFailed}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.68))",
        }}
        aria-hidden
      />
      {handleLabel ? (
        <span
          className="absolute bottom-1.5 left-2 right-2 truncate text-[11px] leading-tight text-white"
          aria-hidden
        >
          {handleLabel}
        </span>
      ) : null}
      {cell.views > 0 ? (
        <span
          className="gv-mono absolute right-1.5 top-1.5 rounded-[3px] bg-black/55 px-1.5 py-0.5 text-[11px] text-white"
          aria-hidden
        >
          {formatViews(cell.views)}
        </span>
      ) : null}
      {cell.content_type === "carousel" ? (
        <span className="absolute left-1.5 top-1.5 z-10">
          <CarouselBadge />
        </span>
      ) : null}
    </div>
  );
}
