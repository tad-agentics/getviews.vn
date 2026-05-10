import { memo, useState } from "react";

import { useTopPatterns, type TopPattern } from "@/hooks/useTopPatterns";
import { PatternCard } from "./PatternCard";
import { PatternModal } from "./PatternModal";

/**
 * Trends — § I PATTERN section.
 *
 * L2.2 Sprint 5 reshape — section now answers "công thức nào đang được
 * video viral trong ngách dùng" (heading "Công thức từ video viral
 * trong ngách"). Cards are filtered to deck-synthesized patterns with
 * within-niche credibility (≥3 videos) and lift (≥1.2× niche median),
 * ranked by lift. Click → ``PatternModal`` opens the deep-teach deck.
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
    <section aria-label="Công thức từ video viral trong ngách" className="mb-14">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="gv-mono mb-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
            § I — PATTERN
          </p>
          <h2 className="gv-tight m-0 text-[clamp(22px,2.5vw,28px)] font-semibold tracking-[-0.02em] text-[color:var(--gv-ink)]">
            Công thức từ video viral trong ngách
          </h2>
        </div>
        <p className="gv-mono whitespace-nowrap text-[10px] uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
          CLICK → HỌC FULL DECK
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
          Chưa đủ công thức có lift cao trong ngách này tuần qua — hệ thống
          đang cập nhật, sẽ có sau khi đủ video tham chiếu.
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
        nicheId={nicheId}
        open={openPattern !== null}
        onOpenChange={(next) => {
          if (!next) setOpenPattern(null);
        }}
      />
    </section>
  );
});
