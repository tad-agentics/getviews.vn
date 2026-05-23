import type { ChannelDepth } from "@/lib/channelDepth";

const DEPTH_PILL_BASE =
  "inline-flex h-10 shrink-0 items-center rounded-md border px-3 text-[13px] leading-tight transition-colors disabled:pointer-events-none disabled:opacity-40";

function depthPillClass(active: boolean): string {
  return active
    ? `${DEPTH_PILL_BASE} border-[var(--gv-ink)] bg-[var(--gv-canvas-2)] font-medium text-[var(--gv-ink)]`
    : `${DEPTH_PILL_BASE} border-[var(--gv-rule)] bg-[var(--gv-paper)] text-[var(--gv-ink-3)] hover:border-[var(--gv-ink-4)] hover:text-[var(--gv-ink)]`;
}

type ChannelDepthPickerProps = {
  depth: ChannelDepth;
  onDepthChange: (depth: ChannelDepth) => void;
  disabled?: boolean;
};

/** §5.1 — Nhanh (0×) vs Sâu (3×) before channel analysis. */
export function ChannelDepthPicker({ depth, onDepthChange, disabled }: ChannelDepthPickerProps) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Mức phân tích kênh">
      <button
        type="button"
        disabled={disabled}
        className={depthPillClass(depth === "nhanh")}
        aria-pressed={depth === "nhanh"}
        onClick={() => onDepthChange("nhanh")}
      >
        Nhanh · 0 credit
      </button>
      <button
        type="button"
        disabled={disabled}
        className={depthPillClass(depth === "sau")}
        aria-pressed={depth === "sau"}
        onClick={() => onDepthChange("sau")}
      >
        Sâu · 3 credit
      </button>
    </div>
  );
}
