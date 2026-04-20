import type { ConfidenceStripData } from "@/lib/api-types";

export function ConfidenceStrip({
  data,
  thinSample,
  onHumilityToggle,
  humilityVisible,
}: {
  data: ConfidenceStripData;
  thinSample: boolean;
  /** Controlled: parent shows `HumilityBanner` when true. */
  onHumilityToggle: () => void;
  humilityVisible: boolean;
}) {
  return (
    <div className="mt-[22px] flex flex-wrap items-center gap-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-3 gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
      <span>
        N={data.sample_size} · {data.window_days} ngày
        {data.niche_scope ? ` · ${data.niche_scope}` : ""} · cập nhật {data.freshness_hours}h trước
      </span>
      {thinSample ? (
        <button
          type="button"
          onClick={onHumilityToggle}
          className={`rounded border px-2 py-0.5 gv-mono text-[10px] uppercase tracking-wide transition-colors ${
            humilityVisible
              ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
              : "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-3)]"
          }`}
          aria-expanded={humilityVisible}
          aria-label="Mẫu mỏng — gợi ý độ tin cậy"
        >
          MẪU MỎNG
        </button>
      ) : null}
    </div>
  );
}
