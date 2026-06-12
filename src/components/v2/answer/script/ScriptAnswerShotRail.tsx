import type { ScriptShotCardData } from "@/lib/api-types";

export function ScriptAnswerShotRail({
  shots,
  activeIndex,
  onSelect,
}: {
  shots: ScriptShotCardData[];
  activeIndex: number;
  onSelect: (index: number) => void;
}) {
  if (shots.length <= 1) return null;

  return (
    <div
      className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      role="tablist"
      aria-label="Tóm tắt từng cảnh"
    >
      {shots.map((shot, i) => {
        const active = i === activeIndex;
        const cam = (shot.cam ?? "").trim() || "—";
        return (
          <button
            // eslint-disable-next-line react/no-array-index-key -- fixed shot list
            key={i}
            type="button"
            role="tab"
            aria-selected={active}
            aria-label={`Cảnh ${i + 1}, ${shot.t0 ?? 0}–${shot.t1 ?? 0} giây, ${cam}`}
            className={
              "flex min-w-[108px] shrink-0 flex-col gap-0.5 rounded-md border px-2.5 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] " +
              (active
                ? "border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                : "border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink)]")
            }
            onClick={() => onSelect(i)}
          >
            <span className="gv-mono text-[11px] font-semibold">Cảnh {i + 1}</span>
            <span className="gv-mono text-[10px] opacity-80">
              {shot.t0 ?? 0}s–{shot.t1 ?? 0}s
            </span>
            <span className="truncate text-[11px] leading-tight opacity-90">{cam}</span>
          </button>
        );
      })}
    </div>
  );
}
