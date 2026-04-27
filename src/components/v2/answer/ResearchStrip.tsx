import { useEffect, useState } from "react";
import { Check } from "lucide-react";

const STEPS = ["Quét", "Phân tích", "Tìm pattern", "Tóm tắt"] as const;

/** Four-step research narrative (Phase C.1.3). */
export function ResearchStepStrip({
  stage,
  done = false,
}: {
  /** 0–3 current highlight while loading; `done` styles all steps complete. */
  stage: number;
  done?: boolean;
}) {
  const activeIndex = done ? STEPS.length : Math.min(Math.max(stage, 0), STEPS.length - 1);
  return (
    <ol className="mt-4 flex flex-wrap gap-2" aria-label="Tiến trình nghiên cứu">
      {STEPS.map((label, i) => {
        const isDone = done || i < activeIndex;
        const isActive = !done && i === activeIndex;
        return (
          <li
            key={label}
            className={`rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wide transition-colors ${
              isDone
                ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-ink)]"
                : isActive
                  ? "border-[color:var(--gv-accent)] bg-[var(--gv-canvas-2)] text-[color:var(--gv-ink)]"
                  : "border-[var(--gv-rule)] text-[var(--gv-ink-4)]"
            }`}
          >
            {label}
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Thanh tiến trình ngang theo reference báo cáo — copy chi tiết + pill hoàn tất.
 */
export function ResearchProcessBar({
  loading,
  stage,
  done,
  videoCount,
  channelCount,
}: {
  loading: boolean;
  stage: number;
  done: boolean;
  videoCount?: number | null;
  channelCount?: number | null;
}) {
  const step = Math.min(Math.max(stage, 0), 3);
  const fmt = (n: number | null | undefined) =>
    n != null && n > 0 ? n.toLocaleString("vi-VN") : null;
  const v = fmt(videoCount);
  const c = fmt(channelCount);

  const labels = [
    v ? `Quét ${v} video` : "Quét video",
    c ? `Phân tích ${c} kênh top` : "Phân tích kênh top",
    "Tìm pattern chung",
    "Viết tóm tắt",
  ] as const;

  return (
    <div
      className="mt-5 flex flex-col gap-3 border-y border-[color:var(--gv-rule)] py-4 min-[700px]:flex-row min-[700px]:items-center min-[700px]:justify-between"
      aria-label="Tiến trình nghiên cứu"
    >
      <ol className="flex min-w-0 flex-1 flex-wrap items-center gap-x-1 gap-y-2 text-[13px] leading-snug text-[color:var(--gv-ink-2)]">
        {labels.map((label, i) => {
          const isDone = done;
          const isActive = !done && loading && i === step;
          return (
            <li key={label} className="flex items-center gap-1">
              {i > 0 ? (
                <span className="mx-1 text-[color:var(--gv-ink-4)]" aria-hidden>
                  ·
                </span>
              ) : null}
              <span
                className={`inline-flex items-center gap-1 ${
                  isDone
                    ? "font-medium text-[color:var(--gv-ink)]"
                    : isActive
                      ? "font-medium text-[color:var(--gv-accent)]"
                      : "text-[color:var(--gv-ink-3)]"
                }`}
              >
                {isDone ? (
                  <Check className="h-3.5 w-3.5 shrink-0 text-[color:var(--gv-pos)]" strokeWidth={2.5} aria-hidden />
                ) : null}
                {label}
              </span>
            </li>
          );
        })}
      </ol>
      {done && !loading ? (
        <p className="shrink-0 rounded-full bg-[color:var(--gv-pos)] px-3 py-1 gv-mono text-[10px] font-semibold uppercase tracking-wide text-white">
          Hoàn tất
        </p>
      ) : loading ? (
        <p className="shrink-0 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[10px] text-[color:var(--gv-ink-3)]">
          Đang chạy…
        </p>
      ) : null}
    </div>
  );
}

/** Cycles stages 0→3 while `active`; resets when inactive. */
export function useResearchStage(active: boolean): number {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    if (!active) {
      setStage(0);
      return;
    }
    const id = window.setInterval(() => {
      setStage((s) => (s >= 3 ? 0 : s + 1));
    }, 450);
    return () => window.clearInterval(id);
  }, [active]);
  return active ? stage : 0;
}

export function ProgressPill({
  loading,
  stepIndex,
  total = 4,
}: {
  loading: boolean;
  stepIndex: number;
  total?: number;
}) {
  if (!loading) return null;
  const n = Math.min(stepIndex + 1, total);
  return (
    <span className="inline-flex items-center rounded-full border border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] px-2 py-0.5 font-mono text-[10px] text-[var(--gv-ink-3)]">
      Đang nghiên cứu… {n}/{total}
    </span>
  );
}

/** Thin activity line under the header during load. */
export function MiniResearchStrip({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div
      className="mt-3 h-0.5 w-full overflow-hidden rounded-full bg-[var(--gv-rule)]"
      aria-hidden
    >
      <div className="h-full w-1/3 animate-pulse rounded-full bg-[color:var(--gv-accent)] motion-reduce:animate-none" />
    </div>
  );
}
