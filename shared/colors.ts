/**
 * Brand color tokens — single source of truth.
 * Populated from EDS §5 Visual Direction during /init or /native-init.
 *
 * Web: src/app.css consumes oklch values via @theme inline
 * Mobile: mobile/tailwind.config.js consumes hex values
 *
 * WARNING: Mobile (NativeWind v4 / TW3) does not support oklch.
 * Always use brand.[color].hex for mobile. oklch is web-only.
 */
export const brand = {
  primary: { hex: "#2563EB", oklch: "oklch(0.55 0.2 260)" },
  background: { hex: "#FFFFFF", oklch: "oklch(1 0 0)" },
  foreground: { hex: "#1A1A1A", oklch: "oklch(0.15 0 0)" },
  surface: { hex: "#F5F5F5", oklch: "oklch(0.97 0 0)" },
  muted: { hex: "#737373", oklch: "oklch(0.55 0 0)" },
  success: { hex: "#16A34A" },
  danger: { hex: "#DC2626" },
  warning: { hex: "#F59E0B" },
} as const;
