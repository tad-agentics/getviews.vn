import { Loader2, Sparkles } from "lucide-react";
import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";
import { overlayStyleVi } from "@/lib/constants/enum-labels-vi";
import { CueChip } from "@/components/v2/CueChip";
import { FormattedVO } from "@/components/v2/FormattedVO";
import { ShotTypeVisual } from "@/components/v2/ShotTypeVisual";
import { ShotReferenceStrip } from "@/components/v2/ShotReferenceStrip";

export type ScriptShotRowProps = {
  shot: ScriptEditorShot;
  idx: number;
  active: boolean;
  onClick: () => void;
  /**
   * S6 — per-shot regenerate. When provided, renders a small "Viết lại"
   * icon button in the top-right of the shot meta column. ``stopPropagation``
   * is applied so it doesn't bubble into the row's selection ``onClick``.
   * ``regenerating`` dims the body + swaps the icon to a spinner while
   * the request is in flight.
   */
  onRegenerate?: () => void;
  regenerating?: boolean;
};

export function ScriptShotRow({
  shot,
  idx,
  active,
  onClick,
  onRegenerate,
  regenerating = false,
}: ScriptShotRowProps) {
  const span = shot.t1 - shot.t0;
  const slow = span > shot.winnerAvg * 1.2;

  return (
    <div
      className={`overflow-hidden bg-[color:var(--gv-paper)] transition-[box-shadow,border-color] duration-100 ${
        active
          ? "border border-[color:var(--gv-ink)] shadow-[3px_3px_0_var(--gv-ink)]"
          : "border border-[color:var(--gv-rule)] shadow-none"
      }`}
    >
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
        className="grid cursor-pointer grid-cols-[90px_100px_1fr_1fr]"
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
        <div className={`border-r border-[color:var(--gv-rule)] p-3 transition-opacity ${regenerating ? "opacity-40" : ""}`}>
          <div className="gv-mono gv-uc mb-1 text-[9px] text-[color:var(--gv-ink-4)]">
            LỜI THOẠI
          </div>
          {shot.vo && shot.vo.length > 0 ? (
            // S5 — structured voice-over (timed lines, inline cues,
            // ``*stress*`` highlights). One row per VO line; t / text /
            // cue mirror ``screens/script.jsx`` lines 1166-1226.
            <div className="flex flex-col gap-1">
              {shot.vo.map((line, li) => (
                <div
                  key={li}
                  className="grid items-baseline gap-2"
                  style={{ gridTemplateColumns: "32px 1fr" }}
                >
                  <span className="gv-mono text-[10px] font-semibold tabular-nums text-[color:var(--gv-ink-4)]">
                    {line.t}
                  </span>
                  <p className="gv-serif font-medium tracking-[-0.025em] text-[13.5px] leading-[1.4] text-[color:var(--gv-ink)] m-0">
                    <FormattedVO text={line.text} />
                    {line.cue ? <CueChip text={line.cue} /> : null}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            // Back-compat: legacy shots without ``vo`` (old drafts before
            // the S5 schema bump landed) keep the flat-string rendering.
            <p className="gv-serif font-semibold tracking-[-0.035em] text-[13.5px] leading-[1.35] text-[color:var(--gv-ink)]">{`"${shot.voice}"`}</p>
          )}
        </div>
        <div className={`relative p-3 transition-opacity ${regenerating ? "opacity-40" : ""}`}>
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
          {onRegenerate ? (
            <button
              type="button"
              onClick={(e) => {
                // Don't bubble — the row's selection handler would steal focus.
                e.stopPropagation();
                if (regenerating) return;
                onRegenerate();
              }}
              disabled={regenerating}
              aria-label="Viết lại shot này"
              className="gv-mono gv-uc absolute right-2 top-2 inline-flex items-center gap-1 rounded-[4px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-1.5 py-0.5 text-[9px] tracking-[0.06em] text-[color:var(--gv-ink-3)] hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)] transition-colors disabled:opacity-60"
            >
              {regenerating ? (
                <Loader2 className="h-2.5 w-2.5 animate-spin" aria-hidden />
              ) : (
                <Sparkles className="h-2.5 w-2.5" aria-hidden />
              )}
              {regenerating ? "đang viết…" : "viết lại"}
            </button>
          ) : null}
        </div>
      </div>
      <ShotReferenceStrip refs={shot.references} />
    </div>
  );
}
