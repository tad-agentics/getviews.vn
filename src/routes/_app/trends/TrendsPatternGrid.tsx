import { memo, useState } from "react";

import { useTopPatterns, type TopPattern } from "@/hooks/useTopPatterns";
import { PatternCard } from "./PatternCard";
import { PatternModal } from "./PatternModal";

/**
 * Trends — § I PATTERN section (PR-T3 + T4).
 *
 * Mirrors the design pack's pattern toolbar + grid (``screens/trends.jsx``
 * lines 387-417). Renders a section header (``§ I — PATTERN`` mono
 * kicker + H2 + ``CLICK PATTERN → MỞ FULL
 * DECK`` mono caption on the right) followed by a 3-column auto-grid
 * of PatternCards (2 cols < 1100px, 1 col < 760px).
 *
 * Click on a card opens the PR-T4 ``PatternModal`` with the pattern
 * pre-selected.
 */

const PATTERN_LIMIT = 6;

export const TrendsPatternGrid = memo(function TrendsPatternGrid({
  nicheId,
}: {
  nicheId: number | null;
}) {
  const { data: patterns = [], isPending } = useTopPatterns(nicheId, PATTERN_LIMIT);
  const [openPattern, setOpenPattern] = useState<TopPattern | null>(null);

  return (
    <section aria-label="Công thức đang chạy tốt" className="mb-14">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="gv-mono mb-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
            § I — PATTERN
          </p>
          <h2 className="gv-tight m-0 text-[clamp(22px,2.5vw,28px)] font-semibold tracking-[-0.02em] text-[color:var(--gv-ink)]">
            6 công thức đang chạy tốt
          </h2>
        </div>
        <p className="gv-mono whitespace-nowrap text-[10px] uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
          CLICK PATTERN → MỞ FULL DECK
        </p>
      </div>

      {/* Grid */}
      {isPending ? (
        <div
          className="grid gap-3.5"
          style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}
        >
          {Array.from({ length: PATTERN_LIMIT }).map((_, i) => (
            <div
              key={i}
              className="aspect-[10/13] animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]"
            />
          ))}
        </div>
      ) : patterns.length === 0 ? (
        <p className="rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-[12.5px] text-[color:var(--gv-ink-3)]">
          Chưa đủ pattern để xếp hạng tuần này — dữ liệu corpus đang cập
          nhật.
        </p>
      ) : (
        <div
          className="grid gap-3.5"
          style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}
        >
          {patterns.map((pattern) => (
            <PatternCard
              key={pattern.id}
              pattern={pattern}
              onOpen={(p) => setOpenPattern(p)}
            />
          ))}
        </div>
      )}

      <PatternModal
        pattern={openPattern}
        open={openPattern !== null}
        onOpenChange={(next) => {
          if (!next) setOpenPattern(null);
        }}
      />
    </section>
  );
});
