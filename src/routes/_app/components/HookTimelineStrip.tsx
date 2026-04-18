import { motion } from "motion/react";

export type HookTimelineEventType =
  | "face_enter"
  | "first_word"
  | "text_overlay"
  | "sound_drop"
  | "cut"
  | "product_enter"
  | "reveal";

export type HookTimelineEvent = {
  t: number;      // seconds, 0.0–3.0
  event: HookTimelineEventType;
  note?: string;
};

const EVENT_COLOR: Record<HookTimelineEventType, string> = {
  face_enter: "bg-purple-500",
  first_word: "bg-blue-500",
  text_overlay: "bg-amber-500",
  sound_drop: "bg-pink-500",
  cut: "bg-slate-500",
  product_enter: "bg-emerald-500",
  reveal: "bg-rose-500",
};

const EVENT_LABEL_VI: Record<HookTimelineEventType, string> = {
  face_enter: "Mặt xuất hiện",
  first_word: "Chữ đầu tiên",
  text_overlay: "Text overlay",
  sound_drop: "Drop âm thanh",
  cut: "Cắt cảnh",
  product_enter: "Sản phẩm vào",
  reveal: "Reveal",
};

/**
 * HookTimelineStrip — compact 0.0s–3.0s "gantt" of hook events.
 *
 * The extraction pipeline (models.HookAnalysis + VIDEO_EXTRACTION_PROMPT)
 * emits 2–5 events in the opening 3-second window. This visual lets a
 * creator see the exact micro-choreography of the hook at a glance —
 * when the face lands, when the text hits, whether there's a reveal cut.
 *
 * Hidden when the list is empty (older analyses pre-hook_timeline).
 */
export function HookTimelineStrip({ events }: { events: HookTimelineEvent[] }) {
  if (!events || events.length === 0) return null;

  // Clamp + sort — defensive against stray server-side values.
  const clean = [...events]
    .filter((e) => typeof e.t === "number" && e.t >= 0 && e.t <= 3.0 && e.event in EVENT_COLOR)
    .sort((a, b) => a.t - b.t);
  if (clean.length === 0) return null;

  return (
    <div className="my-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
        Hook timeline (0–3s)
      </p>
      <div
        className="relative h-9 rounded bg-[var(--surface)] border border-[var(--border)]"
        role="img"
        aria-label="Dòng thời gian 3 giây đầu của hook"
      >
        {/* tick marks at 0s, 1s, 2s, 3s */}
        {[0, 1, 2, 3].map((s) => (
          <div
            key={s}
            className="absolute top-0 bottom-0 w-px bg-[var(--border)]"
            style={{ left: `${(s / 3) * 100}%` }}
          />
        ))}
        {/* event markers */}
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
              title={`${ev.t.toFixed(1)}s — ${EVENT_LABEL_VI[ev.event]}${ev.note ? ` (${ev.note})` : ""}`}
            />
          );
        })}
      </div>
      {/* legend + per-event list (compact) */}
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[var(--muted)]">
        {clean.map((ev, idx) => (
          <li key={idx} className="inline-flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${EVENT_COLOR[ev.event]}`} />
            <span className="tabular-nums text-[var(--ink)]">{ev.t.toFixed(1)}s</span>
            <span>{EVENT_LABEL_VI[ev.event]}</span>
            {ev.note ? <span className="text-[var(--faint)]">· {ev.note}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
