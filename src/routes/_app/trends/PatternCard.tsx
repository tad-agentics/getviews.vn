import { memo } from "react";

import type { PatternVideo, TopPattern } from "@/hooks/useTopPatterns";
import { formatViews } from "@/lib/formatters";
import { lifecycleHint } from "./patternLifecycle";

/**
 * Trends — PatternCard (PR-T3 §I).
 *
 * Mirrors the design pack's PatternCard (``screens/trends.jsx`` lines
 * 570-639): a 2×2 video collage at top + body with title/sub +
 * star save toggle (placeholder, no-op until a saved-patterns feature
 * lands) + 3-stat strip (VIDEO / VIEW TB / GIỮ%) + lifecycle dot.
 *
 * Card click fires ``onOpen`` — the consuming screen wires this to
 * the PatternModal in PR-T4. T3 ships with the click handler in place
 * and an empty body so the card stays interactive.
 *
 * GIỮ% renders ``"—"`` for now — per-video retention isn't reliably
 * persisted on ``video_corpus``. PR-T4 / a future BE PR can plumb
 * ``avg_completion_rate`` from ``hook_effectiveness`` when available.
 */

const COLLAGE_FALLBACK_BG: ReadonlyArray<string> = [
  "bg-[color:var(--gv-canvas-2)]",
  "bg-[color:var(--gv-rule)]",
  "bg-[color:var(--gv-canvas)]",
  "bg-[color:var(--gv-rule-2,var(--gv-rule))]",
];

export const PatternCard = memo(function PatternCard({
  pattern,
  onOpen,
}: {
  pattern: TopPattern;
  onOpen?: (pattern: TopPattern) => void;
}) {
  const lifecycle = lifecycleHint(
    pattern.weekly_instance_count,
    pattern.weekly_instance_count_prev,
  );
  const collageCells = padCollage(pattern.videos);
  const dotColor = lifecycle.isFresh
    ? "bg-[color:var(--gv-pos)]"
    : "bg-[color:var(--gv-ink-3)]";
  const sub = pattern.sample_hook?.trim()
    ? `"${pattern.sample_hook.trim()}"`
    : "—";

  return (
    <article
      className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] transition-transform duration-150 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_rgba(0,0,0,0.18)]"
    >
      <button
        type="button"
        onClick={() => onOpen?.(pattern)}
        className="flex h-full w-full flex-col text-left"
        aria-label={`Mở pattern: ${pattern.display_name}`}
      >
        {/* 2×2 collage */}
        <div
          className="grid grid-cols-2 gap-px bg-[color:var(--gv-rule)]"
          style={{ aspectRatio: "16 / 10" }}
          aria-hidden
        >
          {collageCells.map((cell, i) => (
            <CollageTile key={i} cell={cell} index={i} />
          ))}
        </div>
        {/* Body */}
        <div className="flex flex-col gap-2 px-3.5 py-3.5">
          <div className="min-w-0">
            <h3 className="gv-tight m-0 text-[17px] font-semibold leading-[1.15] tracking-[-0.02em] text-[color:var(--gv-ink)] line-clamp-2">
              {pattern.display_name}
            </h3>
            <p className="gv-serif-italic mt-1 text-[11px] leading-[1.4] text-[color:var(--gv-ink-3)] line-clamp-2">
              {sub}
            </p>
          </div>
          {/* Stat strip */}
          <div className="grid grid-cols-3 gap-1.5 border-t border-b border-[color:var(--gv-rule)] py-2">
            <Stat label="VIDEO" value={String(pattern.instance_count)} />
            <Stat
              label="VIEW TB"
              value={pattern.avg_views != null ? formatViews(pattern.avg_views) : "—"}
            />
            <Stat label="GIỮ" value="—" />
          </div>
          {/* Lifecycle hint */}
          <div className="gv-mono flex items-center gap-1.5 text-[10px] text-[color:var(--gv-ink-3)]">
            <span
              className={`inline-block h-[5px] w-[5px] rounded-full ${dotColor}`}
              aria-hidden
            />
            {lifecycle.text}
          </div>
        </div>
      </button>
    </article>
  );
});

function CollageTile({
  cell,
  index,
}: {
  cell: PatternVideo | null;
  index: number;
}) {
  const fallback = COLLAGE_FALLBACK_BG[index % COLLAGE_FALLBACK_BG.length];
  if (!cell) {
    return <div className={`${fallback} relative overflow-hidden`} aria-hidden />;
  }
  const handleLabel = (cell.creator_handle ?? "").startsWith("@")
    ? cell.creator_handle
    : cell.creator_handle
      ? `@${cell.creator_handle}`
      : null;
  return (
    <div className={`${fallback} relative overflow-hidden`}>
      {cell.thumbnail_url ? (
        <img
          src={cell.thumbnail_url}
          alt=""
          loading="lazy"
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : null}
      {/* Bottom shadow gradient for handle legibility */}
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
          className="absolute bottom-1.5 left-2 right-2 truncate text-[10px] leading-tight text-white"
          aria-hidden
        >
          {handleLabel}
        </span>
      ) : null}
      {cell.views > 0 ? (
        <span
          className="gv-mono absolute right-1.5 top-1.5 rounded-[3px] bg-black/55 px-1.5 py-0.5 text-[9px] text-white"
          aria-hidden
        >
          ↑{formatViews(cell.views)}
        </span>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="gv-mono mb-0.5 text-[8px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
        {label}
      </p>
      <p className="m-0 text-[13px] font-semibold leading-none tracking-[-0.01em] text-[color:var(--gv-ink)]">
        {value}
      </p>
    </div>
  );
}

/** Pad a videos array to exactly 4 entries with nulls so the 2×2 grid
 *  never collapses on patterns with < 4 corpus rows. */
function padCollage(videos: ReadonlyArray<PatternVideo>): Array<PatternVideo | null> {
  const out: Array<PatternVideo | null> = [...videos.slice(0, 4)];
  while (out.length < 4) out.push(null);
  return out;
}
