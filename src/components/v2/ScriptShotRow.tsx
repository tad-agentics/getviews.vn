import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";
import { overlayStyleVi } from "@/lib/constants/enum-labels-vi";
import { ShotTypeVisual } from "@/components/v2/ShotTypeVisual";

export type ScriptShotRowProps = {
  shot: ScriptEditorShot;
  idx: number;
  active: boolean;
  onClick: () => void;
};

export function ScriptShotRow({ shot, idx, active, onClick }: ScriptShotRowProps) {
  const span = shot.t1 - shot.t0;
  const slow = span > shot.winnerAvg * 1.2;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className={`grid cursor-pointer grid-cols-[90px_100px_1fr_1fr] overflow-hidden bg-[color:var(--gv-paper)] transition-[box-shadow,border-color] duration-100 ${
        active
          ? "border border-[color:var(--gv-ink)] shadow-[3px_3px_0_var(--gv-ink)]"
          : "border border-[color:var(--gv-rule)] shadow-none"
      }`}
    >
      <div
        className={`p-3 ${
          active
            ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
            : idx === 0
              ? "bg-[color:var(--gv-accent)] text-[color:var(--gv-canvas)]"
              : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-2)]"
        }`}
      >
        <div className="gv-mono mb-1 text-[10px] opacity-70">SHOT {String(idx + 1).padStart(2, "0")}</div>
        <div className="gv-mono text-xs font-semibold">
          {shot.t0}–{shot.t1}s
        </div>
        <div className="gv-mono mt-1 text-[9px] opacity-70">{span}s</div>
      </div>
      <ShotTypeVisual intelSceneType={shot.intelSceneType} cam={shot.cam} />
      <div className="border-r border-[color:var(--gv-rule)] p-3">
        <div className="gv-mono gv-uc mb-1 text-[9px] text-[color:var(--gv-ink-4)]">
          LỜI THOẠI
        </div>
        <p className="gv-serif font-semibold tracking-[-0.035em] text-[13.5px] leading-[1.35] text-[color:var(--gv-ink)]">{`"${shot.voice}"`}</p>
      </div>
      <div className="relative p-3">
        <div className="gv-mono gv-uc mb-1 text-[9px] text-[color:var(--gv-ink-4)]">
          HÌNH ẢNH · {overlayStyleVi(shot.overlay, shot.overlay)}
        </div>
        <p className="mb-2 text-xs leading-[1.4] text-[color:var(--gv-ink-3)]">{shot.viz}</p>
        <div
          className={`gv-mono inline-flex items-center gap-[5px] rounded-[3px] px-[7px] py-0.5 text-[10px] font-medium ${
            slow
              ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
              : "bg-[rgba(0,159,250,0.12)] text-[rgb(0,159,250)]"
          }`}
        >
          {slow ? "⚠" : "✓"} {span.toFixed(1)}s · ngách {shot.winnerAvg}s
        </div>
      </div>
    </div>
  );
}
