import type { SVGAttributes } from "react";

/**
 * Branded glyph set — Getviews iconography v1.
 *
 * Source: design pack `icons.jsx` cases `spike` / `window` / `hook` / `decode`,
 * spec from Branding Guideline §06. 24×24 viewBox, square caps, miter joins,
 * `currentColor` only. Stroke compensates for size so hairlines stay visible
 * (14→2.2 · 18→2.0 · 24→1.6 · 32→1.4 · ≥48→1.2).
 *
 * The four glyphs encode the product's narrative:
 *   spike   — the trend going vertical (Trends, Studio nav)
 *   window  — observation surface (analysis, Video screens)
 *   hook    — the curl of a fishing hook (hook patterns)
 *   decode  — bars + arrow → split column (signal → action; Studio promise)
 *
 * Lucide stays the workhorse for the rest of the icon set; this component is
 * for places where the brand mark itself is the point.
 */

export type BrandGlyphName = "spike" | "window" | "hook" | "decode";

function strokeForSize(size: number): number {
  if (size <= 14) return 2.2;
  if (size <= 18) return 2.0;
  if (size <= 24) return 1.6;
  if (size <= 32) return 1.4;
  return 1.2;
}

type BrandGlyphProps = {
  name: BrandGlyphName;
  size?: number;
  stroke?: number;
} & Omit<SVGAttributes<SVGSVGElement>, "stroke">;

export function BrandGlyph({
  name,
  size = 24,
  stroke,
  className,
  style,
  ...rest
}: BrandGlyphProps) {
  const sw = stroke ?? strokeForSize(size);
  const svgProps = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: sw,
    strokeLinecap: "square" as const,
    strokeLinejoin: "miter" as const,
    style: { display: "block", ...style },
    className,
    "aria-hidden": rest["aria-label"] ? undefined : true,
    ...rest,
  };

  switch (name) {
    case "spike":
      return (
        <svg {...svgProps}>
          <line x1="3" y1="20" x2="21" y2="20" />
          <polyline points="4 16 9 13 13 15 19 7" />
          <circle cx="19" cy="7" r="1.6" fill="currentColor" stroke="none" />
        </svg>
      );
    case "window":
      return (
        <svg {...svgProps}>
          <polyline points="6 4 4 4 4 20 6 20" />
          <polyline points="18 4 20 4 20 20 18 20" />
          <circle cx="12" cy="12" r="3.5" />
          <polyline points="12 10 12 12 13.5 13" />
        </svg>
      );
    case "hook":
      return (
        <svg {...svgProps}>
          <line x1="12" y1="3" x2="12" y2="11" />
          <path d="M12 11C12 14 9 16 6 16C7 18 9 19 12 19" />
          <line x1="3" y1="12" x2="6" y2="12" />
        </svg>
      );
    case "decode":
      return (
        <svg {...svgProps}>
          <line x1="3" y1="6" x2="9" y2="6" />
          <line x1="3" y1="12" x2="9" y2="12" />
          <line x1="3" y1="18" x2="9" y2="18" />
          <polyline points="13 8 17 12 13 16" />
          <line x1="11" y1="12" x2="21" y2="12" />
        </svg>
      );
  }
}
