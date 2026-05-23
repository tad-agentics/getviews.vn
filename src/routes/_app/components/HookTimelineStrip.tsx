import { motion } from "motion/react";

import type { HookTimelineEvent, HookTimelineEventType } from "@/lib/api-types";
import { HOOK_TIMELINE_EVENT_VI } from "@/lib/hookTimelineLabels";

export type { HookTimelineEvent, HookTimelineEventType };

const EVENT_COLOR: Record<HookTimelineEventType, string> = {
  face_enter: "bg-[color:var(--gv-accent)]",
  first_word: "bg-[color:var(--gv-pos)]",
  text_overlay: "bg-[color:var(--gv-warn)]",
  sound_drop: "bg-[color:var(--gv-accent-deep)]",
  cut: "bg-[color:var(--gv-ink-3)]",
  product_enter: "bg-[color:var(--gv-pos-deep)]",
  reveal: "bg-[color:var(--gv-danger)]",
};

/**
 * HookTimelineStrip — compact 0.0s–3.0s timeline of hook micro-events.
 * Hidden when the list is empty (older analyses pre-hook_timeline).
 */
export function HookTimelineStrip({ events }: { events: HookTimelineEvent[] }) {
  if (!events || events.length === 0) return null;

  const clean = [...events]
    .filter((e) => typeof e.t === "number" && e.t >= 0 && e.t <= 3.0 && e.event in EVENT_COLOR)
    .sort((a, b) => a.t - b.t);
  if (clean.length === 0) return null;

  return (
    <div className="my-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3">
      <p className="gv-kicker mb-2 text-[color:var(--gv-ink-3)]">
        Dòng thời gian hook · 0–3 giây
      </p>
      <div
        className="relative h-9 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]"
        role="img"
        aria-label="Dòng thời gian 3 giây đầu của hook"
      >
        {[0, 1, 2, 3].map((s) => (
          <div
            key={s}
            className="absolute top-0 bottom-0 w-px bg-[color:var(--gv-rule)]"
            style={{ left: `${(s / 3) * 100}%` }}
          />
        ))}
        {clean.map((ev, idx) => {
          const left = Math.min(99, (ev.t / 3) * 100);
          return (
            <motion.div
              key={`${idx}-${ev.t}`}
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2, delay: idx * 0.05 }}
              className={`absolute top-1/2 -translate-y-1/2 h-5 w-1.5 rounded ${EVENT_COLOR[ev.event]}`}
              style={{ left: `${left}%` }}
              title={`${ev.t.toFixed(1)}s — ${HOOK_TIMELINE_EVENT_VI[ev.event]}${ev.note ? ` (${ev.note})` : ""}`}
            />
          );
        })}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[color:var(--gv-ink-3)]">
        {clean.map((ev, idx) => (
          <li key={idx} className="inline-flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${EVENT_COLOR[ev.event]}`} />
            <span className="gv-mono tabular-nums text-[color:var(--gv-ink)]">{ev.t.toFixed(1)}s</span>
            <span>{HOOK_TIMELINE_EVENT_VI[ev.event]}</span>
            {ev.note ? <span className="text-[color:var(--gv-ink-4)]">· {ev.note}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
