import { memo, useState } from "react";

import { ConfidenceStrip } from "@/components/v2/answer/pattern/ConfidenceStrip";
import { HumilityBanner } from "@/components/v2/answer/pattern/HumilityBanner";
import { useTopPatterns, type TopPattern, type TopPatternsScope } from "@/hooks/useTopPatterns";
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
  patternScope,
  legacyNicheId = null,
  thinSample = false,
  thinSampleCount = 0,
  nicheScopeLabel = null,
  freshnessHours = 24,
}: {
  patternScope: TopPatternsScope;
  /** PatternModal still keys related corpus on legacy id when set. */
  legacyNicheId?: number | null;
  thinSample?: boolean;
  thinSampleCount?: number;
  nicheScopeLabel?: string | null;
  freshnessHours?: number;
}) {
  const { data: patterns = [], isPending } = useTopPatterns(patternScope, PATTERN_LIMIT);
  const [openPattern, setOpenPattern] = useState<TopPattern | null>(null);
  const [humilityOpen, setHumilityOpen] = useState(true);

  const confidenceStrip = thinSample ? (
    <>
      <ConfidenceStrip
        data={{
          sample_size: thinSampleCount,
          window_days: 7,
          niche_scope: nicheScopeLabel,
          freshness_hours: freshnessHours,
          intent_confidence: "low",
          what_stalled_reason: null,
        }}
        thinSample
        humilityVisible={humilityOpen}
        onHumilityToggle={() => setHumilityOpen((v) => !v)}
      />
      {humilityOpen ? (
        <div className="mb-4">
          <HumilityBanner />
        </div>
      ) : null}
    </>
  ) : null;

  return (
    <section aria-label="Công thức từ video view cao trong ngách" className="mb-14">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="gv-mono mb-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
            Phần I — Pattern
          </p>
          <h2 className="gv-tight m-0 text-[clamp(22px,2.5vw,28px)] font-semibold tracking-[-0.02em] text-[color:var(--gv-ink)]">
            Công thức từ video view cao trong ngách
          </h2>
        </div>
        <p className="gv-mono max-w-[200px] text-right text-[10px] leading-snug tracking-[0.06em] text-[color:var(--gv-ink-4)]">
          Chạm thẻ để xem công thức đầy đủ.
        </p>
      </div>

      {confidenceStrip}

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
        nicheId={legacyNicheId}
        open={openPattern !== null}
        onOpenChange={(next) => {
          if (!next) setOpenPattern(null);
        }}
      />
    </section>
  );
});
