import { memo } from "react";

/**
 * Studio Home — bridge ribbon at the bottom of HomeMyChannelSection (PR-4).
 *
 * Mirrors the design pack's ink-filled ribbon spec (lines 833-847 in
 * ``screens/home.jsx``):
 *   • mono-uppercase coral kicker "→ TIẾP THEO"
 *   • single-line serif body explaining the bridge
 *   • coral pill button on the right ("Xem gợi ý ↓") that scrolls to
 *     tier 01 of HomeSuggestionsToday.
 *
 * The actual scroll lives in ``scrollToTier.ts``; this component is
 * wired with ``onScrollToSuggestions`` so the channel section can
 * compose its own behaviour (e.g. focus-after-scroll later).
 */

export const ChannelBridgeRibbon = memo(function ChannelBridgeRibbon({
  onScrollToSuggestions,
}: {
  onScrollToSuggestions: () => void;
}) {
  return (
    <section
      aria-label="Bridge sang Gợi ý hôm nay"
      className="flex flex-wrap items-center justify-between gap-3.5 bg-[color:var(--gv-ink)] px-5 py-4 text-[color:var(--gv-canvas)] sm:px-6"
    >
      <div className="min-w-0 flex-1">
        <p className="gv-mono mb-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[color:var(--gv-accent)]">
          → TIẾP THEO
        </p>
        <p
          className="m-0 text-[14px] leading-snug tracking-[-0.01em] text-[color:var(--gv-canvas)]"
          style={{ fontFamily: "var(--gv-font-display)", textWrap: "pretty" }}
        >
          Gợi ý hôm nay đã ưu tiên các ý tưởng bám theo điểm mạnh & sửa điểm yếu phía trên.
        </p>
      </div>
      <button
        type="button"
        onClick={onScrollToSuggestions}
        className="gv-mono shrink-0 whitespace-nowrap rounded-[4px] bg-[color:var(--gv-accent)] px-3.5 py-2 text-[10px] font-bold uppercase tracking-[0.1em] text-white transition-colors hover:bg-[color:var(--gv-accent-deep)]"
      >
        Xem gợi ý ↓
      </button>
    </section>
  );
});
