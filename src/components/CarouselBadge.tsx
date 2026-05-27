/** HI-16 — badge for photo carousel corpus rows (distinct from video format chips). */
export function CarouselBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={
        "gv-mono shrink-0 rounded border border-[color:var(--gv-accent-deep)]/35 " +
        "bg-[color:color-mix(in_srgb,var(--gv-accent)_12%,var(--gv-paper))] " +
        "px-1.5 py-px text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-accent-deep)] " +
        className
      }
    >
      Carousel
    </span>
  );
}
