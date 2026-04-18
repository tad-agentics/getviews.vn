import type { ReactNode } from "react";

export type SegmentedOption<V extends string> = {
  value: V;
  label: ReactNode;
};

/**
 * Hard-edge 2-button segmented control. Flat 1px ink border, ink-filled on
 * active. Used for the video screen's Win/Flop toggle and the kol screen's
 * "Đang theo dõi / Khám phá" tabs.
 */
export function Segmented<V extends string>({
  value,
  options,
  onChange,
  className,
}: {
  value: V;
  options: readonly SegmentedOption<V>[];
  onChange: (v: V) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={[
        "inline-flex border border-[color:var(--gv-ink)] rounded-[6px] overflow-hidden",
        className ?? "",
      ].filter(Boolean).join(" ")}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.value)}
            className={
              "px-4 py-2 text-xs font-medium transition-colors " +
              (active
                ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                : "bg-transparent text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)]")
            }
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
