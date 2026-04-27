/**
 * SignalBadge — colored pill showing trend signal strength.
 *
 * signal values (from trend_card JSON schema):
 *   "rising"    → ▲ Đang bùng    — green bg, up-arrow glyph
 *   "early"     → ● Tín hiệu sớm — amber bg
 *   "stable"    → ● Ổn định      — neutral bg
 *   "declining" → ▼ Đang giảm    — red bg, down-arrow glyph
 *
 * CLAUDE.md copy-rule: prefer typographic glyphs (✕/✓/●/▲/▼) to emoji,
 * which render unevenly across Vietnamese fonts on Android and Windows
 * Chrome. Colour comes from semantic tokens, so colour-blind users can
 * still read the direction from the glyph + the Vietnamese label.
 */

export type SignalValue = "rising" | "early" | "stable" | "declining";

// Background + foreground colours come from semantic tokens in
// ``src/app.css`` (``--gv-signal-*-bg`` / ``--gv-signal-*-fg``).
// The component just looks them up; no inline hex colours.
const SIGNAL_CONFIG: Record<
  SignalValue,
  { label: string; dot: string; bg: string; text: string }
> = {
  rising: {
    label: "Đang bùng",
    dot: "▲",
    bg: "var(--gv-signal-rising-bg)",
    text: "var(--gv-signal-rising-fg)",
  },
  early: {
    label: "Tín hiệu sớm",
    dot: "●",
    bg: "var(--gv-signal-early-bg)",
    text: "var(--gv-signal-early-fg)",
  },
  stable: {
    label: "Ổn định",
    dot: "●",
    bg: "var(--gv-signal-stable-bg)",
    text: "var(--gv-signal-stable-fg)",
  },
  declining: {
    label: "Đang giảm",
    dot: "▼",
    bg: "var(--gv-signal-declining-bg)",
    text: "var(--gv-signal-declining-fg)",
  },
};

interface Props {
  signal: string;
  size?: "sm" | "md";
}

export function SignalBadge({ signal, size = "sm" }: Props) {
  const cfg = SIGNAL_CONFIG[signal as SignalValue] ?? {
    label: signal,
    dot: "●",
    bg: "var(--gv-signal-stable-bg)",
    text: "var(--gv-signal-stable-fg)",
  };

  const fontSize = size === "md" ? "0.75rem" : "0.625rem";
  const px = size === "md" ? "8px" : "6px";
  const py = size === "md" ? "4px" : "2px";

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full font-semibold leading-none"
      style={{
        background: cfg.bg,
        color: cfg.text,
        fontSize,
        padding: `${py} ${px}`,
      }}
    >
      <span aria-hidden>{cfg.dot}</span>
      {cfg.label}
    </span>
  );
}
