/**
 * SignalBadge — colored pill showing trend signal strength.
 *
 * signal values (from trend_card JSON schema):
 *   "rising"    → 🟢 Đang bùng    — green bg
 *   "early"     → 🟡 Tín hiệu sớm — amber bg
 *   "stable"    → ⚫ Ổn định       — neutral bg
 *   "declining" → 🔴 Đang giảm    — red bg
 */

export type SignalValue = "rising" | "early" | "stable" | "declining";

const SIGNAL_CONFIG: Record<
  SignalValue,
  { label: string; dot: string; bg: string; text: string }
> = {
  rising: {
    label: "Đang bùng",
    dot: "🟢",
    bg: "rgba(34,197,94,0.12)",
    text: "#16a34a",
  },
  early: {
    label: "Tín hiệu sớm",
    dot: "🟡",
    bg: "rgba(234,179,8,0.12)",
    text: "#ca8a04",
  },
  stable: {
    label: "Ổn định",
    dot: "⚫",
    bg: "rgba(113,113,122,0.10)",
    text: "var(--muted)",
  },
  declining: {
    label: "Đang giảm",
    dot: "🔴",
    bg: "rgba(239,68,68,0.10)",
    text: "#dc2626",
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
    bg: "rgba(113,113,122,0.10)",
    text: "var(--muted)",
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
      <span style={{ fontSize: "0.65em" }}>{cfg.dot}</span>
      {cfg.label}
    </span>
  );
}
