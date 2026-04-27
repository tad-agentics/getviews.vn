/**
 * S5 — CueChip renders an inline directorial tag from a VO line's
 * ``cue`` field (per design pack ``screens/script.jsx`` lines 1253-1268).
 *
 * Design taxonomy + colour coding:
 *   - pause   ("dừng …" / "pause") → muted ink — these are timing beats.
 *   - cut     ("CUT …" / "B-roll" / "overlay") → accent-2 (sky) — these
 *     are visual cuts the editor needs to act on.
 *   - sfx     ("SFX …" / "silence" / "click" / "pop") → purple — these
 *     are audio cues that don't get baked into VO.
 *   - generic — falls back to muted ink so unknown tags still render.
 *
 * The bracket pair ``[…]`` from the BE is stripped so the chip only
 * shows the inner copy. Empty / whitespace cues render nothing.
 */

type CueKind = "pause" | "cut" | "sfx" | "generic";

function classifyCue(text: string): CueKind {
  if (/dừng|pause/i.test(text)) return "pause";
  if (/CUT|B[- ]?roll|overlay/i.test(text)) return "cut";
  if (/SFX|silence|click|pop/i.test(text)) return "sfx";
  return "generic";
}

const CUE_STYLES: Record<CueKind, string> = {
  pause:
    "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)] border border-[color:var(--gv-rule)]",
  cut:
    "bg-[color:var(--gv-accent-2-soft)] text-[color:var(--gv-accent-2-deep)] border border-[color:var(--gv-accent-2-deep)]",
  sfx:
    "bg-[color:rgba(120,80,160,0.08)] text-[color:rgb(120,80,160)] border border-[color:rgba(120,80,160,0.4)]",
  generic:
    "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)] border border-[color:var(--gv-rule)]",
};

export function CueChip({ text }: { text: string | null | undefined }) {
  const trimmed = (text ?? "").trim();
  if (!trimmed) return null;
  const kind = classifyCue(trimmed);
  const inner = trimmed.replace(/^\[|\]$/g, "");
  return (
    <span
      className={`gv-mono inline-block ml-2 align-middle rounded-[3px] px-1.5 py-[1px] text-[10.5px] font-medium opacity-90 ${CUE_STYLES[kind]}`}
      data-cue-kind={kind}
    >
      {inner}
    </span>
  );
}
