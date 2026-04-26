import { memo } from "react";
import type { ChannelPulse } from "@/lib/api-types";

/**
 * Studio Home pulse hero (PR-1 / design pack §A.).
 *
 * Renders the canvas-2 strip below the kênh's identity row inside
 * ``HomeMyChannelSection``'s ConnectedCard:
 *   • status dot + "STREAK X/14 NGÀY" mono kicker
 *   • one-sentence serif headline (italic when emotionally weighted)
 *
 * Hidden entirely if the BE didn't send a pulse payload (older cached
 * responses) or when the streak is 0 AND the headline is empty.
 *
 * Source of truth for the headline + headline_kind:
 * ``cloud-run/getviews_pipeline/channel_analyze.py::_compute_pulse``.
 */

const KIND_TONE: Record<ChannelPulse["headline_kind"], { dot: string; kicker: string }> = {
  win: {
    dot: "var(--gv-pos)",
    kicker: "text-[color:var(--gv-pos-deep)]",
  },
  concern: {
    dot: "var(--gv-neg)",
    kicker: "text-[color:var(--gv-neg-deep)]",
  },
  neutral: {
    dot: "var(--gv-ink-4)",
    kicker: "text-[color:var(--gv-ink-3)]",
  },
};

export const ChannelPulseBlock = memo(function ChannelPulseBlock({
  pulse,
}: {
  pulse: ChannelPulse;
}) {
  if (!pulse.headline) return null;
  const tone = KIND_TONE[pulse.headline_kind] ?? KIND_TONE.neutral;
  const showStreak = pulse.streak_days >= 1;
  return (
    <section
      aria-label="Pulse kênh"
      className="border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-5 py-5 sm:px-6"
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          className="inline-block h-2 w-2 shrink-0 rounded-full"
          style={{
            background: tone.dot,
            // Soft halo per the design's PulseBlock spec.
            boxShadow: `0 0 0 3px color-mix(in srgb, ${tone.dot} 25%, transparent)`,
          }}
          aria-hidden
        />
        <span
          className={
            "gv-mono text-[10px] font-semibold uppercase tracking-[0.1em] " + tone.kicker
          }
        >
          {showStreak
            ? `STREAK ${pulse.streak_days}/${pulse.streak_window} NGÀY`
            : "PULSE KÊNH"}
        </span>
      </div>
      <p
        className="m-0 max-w-prose text-[19px] font-medium leading-[1.4] tracking-[-0.005em] text-[color:var(--gv-ink)]"
        style={{
          fontFamily: "var(--gv-font-display)",
          textWrap: "pretty",
        }}
      >
        {pulse.headline}
      </p>
    </section>
  );
});
