/**
 * AgentStepLogger — renders real-time pipeline step events (P0-6).
 *
 * Visual spec:
 *   Phase header (step_start/step_process):  --ink, font-weight 600, rotating spinner → ✓ on done
 *   Search query (step_search):              --muted, font-weight 400, 16px left indent, fade-in 200ms
 *   Count line (step_count):                 --ink, font-weight 600, formatVN(count) + thumbnail circles
 *   Creator handle (step_creator):           --purple, font-weight 500, 16px left indent
 *   Phase complete (step_done):              collapses children to single "✓ summary" line (300ms)
 *   Synthesis starts:                        all logs collapse to 1px --border separator
 *
 * When `collapsed` is true (synthesis is streaming) the entire logger is replaced
 * by a 1px divider line — animation handled by parent (ChatScreen).
 */
import { motion, AnimatePresence } from "motion/react";
import type { StepEvent } from "@/lib/types/sse-events";
import { StepSpinner } from "./StepSpinner";
import { StepThumbnails } from "./StepThumbnails";
import { formatVN } from "@/lib/formatters";

interface Props {
  events: StepEvent[];
  /** True when synthesis text has started streaming — collapse the logger. */
  collapsed?: boolean;
}

interface PhaseGroup {
  header: string;
  done: boolean;
  doneSummary?: string;
  children: StepEvent[];
}

/** Group flat event list into phases separated by step_start / step_process headers. */
function groupPhases(events: StepEvent[]): PhaseGroup[] {
  const groups: PhaseGroup[] = [];
  let current: PhaseGroup | null = null;

  for (const ev of events) {
    if (ev.type === "step_start" || ev.type === "step_process") {
      current = { header: ev.label, done: false, children: [] };
      groups.push(current);
    } else if (ev.type === "step_done") {
      if (current) {
        current.done = true;
        current.doneSummary = ev.summary;
      } else {
        // Orphan done event — create implicit phase
        groups.push({ header: ev.summary, done: true, doneSummary: ev.summary, children: [] });
      }
      current = null;
    } else {
      if (!current) {
        // Event before first header — create implicit phase
        current = { header: "", done: false, children: [] };
        groups.push(current);
      }
      current.children.push(ev);
    }
  }

  return groups;
}

function StepChild({ event }: { event: StepEvent }) {
  switch (event.type) {
    case "step_search":
      return (
        <motion.div
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2 }}
          className="ml-4 flex items-center gap-1.5"
        >
          <span className="text-xs text-[var(--muted)]">
            {event.source === "corpus" ? "📂" : "🔍"}
          </span>
          <span className="text-xs text-[var(--muted)]">"{event.query}"</span>
        </motion.div>
      );

    case "step_creator":
      return (
        <motion.div
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2 }}
          className="ml-4"
        >
          <span className="text-xs font-medium text-[var(--purple)]">{event.handle}</span>
        </motion.div>
      );

    case "step_count":
      return (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="ml-4 flex items-center gap-2"
        >
          <span className="text-xs font-semibold text-[var(--ink)]">
            Đã tìm {formatVN(event.count)} video
          </span>
          {event.thumbnails?.length > 0 ? (
            <StepThumbnails thumbnails={event.thumbnails} />
          ) : null}
        </motion.div>
      );

    default:
      return null;
  }
}

function PhaseRow({ phase, isLast }: { phase: PhaseGroup; isLast: boolean }) {
  const isActive = !phase.done && isLast;

  return (
    <div className="flex flex-col gap-1">
      {/* Phase header */}
      <div className="flex items-center gap-2">
        <StepSpinner done={phase.done} size={12} />
        <span
          className="text-xs font-semibold leading-snug"
          style={{ color: phase.done ? "var(--muted)" : "var(--ink)" }}
        >
          {phase.done ? (phase.doneSummary ?? phase.header) : phase.header}
        </span>
      </div>

      {/* Children — only shown when not done (collapsed to summary) */}
      <AnimatePresence>
        {!phase.done && isActive && phase.children.length > 0 ? (
          <motion.div
            initial={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden flex flex-col gap-1 py-0.5"
          >
            {phase.children.map((child, i) => (
              <StepChild key={i} event={child} />
            ))}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export function AgentStepLogger({ events, collapsed = false }: Props) {
  if (!events.length && !collapsed) return null;

  const phases = groupPhases(events);

  if (collapsed) {
    return (
      <motion.div
        initial={{ opacity: 1, height: "auto" }}
        animate={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="overflow-hidden"
      >
        <div className="border-b border-[var(--border)]" />
      </motion.div>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mb-3 flex flex-col gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2.5"
      >
        {phases.map((phase, i) => (
          <PhaseRow key={i} phase={phase} isLast={i === phases.length - 1} />
        ))}

        {/* Live indicator when last phase is still active */}
        {phases.length > 0 && !phases[phases.length - 1].done ? (
          <motion.div
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
            className="mt-0.5 text-[10px] text-[var(--faint)] tracking-wider uppercase"
          >
            đang xử lý…
          </motion.div>
        ) : null}
      </motion.div>
    </AnimatePresence>
  );
}
