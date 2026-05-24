import { useLayoutEffect, useRef } from "react";

const MIN_SCALE = 0.55;

function measureOverflowScale(containerWidth: number, lines: HTMLElement[]): number {
  let scale = 1;
  for (const line of lines) {
    if (line.scrollWidth > containerWidth) {
      scale = Math.min(scale, containerWidth / line.scrollWidth);
    }
  }
  return Math.max(MIN_SCALE, Math.min(1, scale));
}

/**
 * Shrinks Studio Home greeting lines via ``--gv-greeting-scale`` when nowrap
 * copy (long niche names) would overflow the headline column.
 */
export function useHomeGreetingFit(deps: readonly unknown[]) {
  const containerRef = useRef<HTMLHeadingElement>(null);
  const line1Ref = useRef<HTMLSpanElement>(null);
  const line2Ref = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const lines = [line1Ref.current, line2Ref.current].filter(Boolean) as HTMLElement[];
    if (!container || lines.length === 0) return;

    const fit = () => {
      container.style.setProperty("--gv-greeting-scale", "1");
      const width = container.clientWidth;
      if (width <= 0) return;

      let scale = measureOverflowScale(width, lines);
      container.style.setProperty("--gv-greeting-scale", String(scale));

      const refined = measureOverflowScale(width, lines);
      if (refined < 1) {
        scale = Math.max(MIN_SCALE, scale * refined);
        container.style.setProperty("--gv-greeting-scale", String(scale));
      }
    };

    fit();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(fit);
    ro.observe(container);
    for (const line of lines) ro.observe(line);
    return () => ro.disconnect();
  }, deps);

  return { containerRef, line1Ref, line2Ref };
}
