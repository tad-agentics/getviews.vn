/** Skeleton shown while a lazy `/app/*` route module or screen chunk loads. */
export function RouteScreenFallback({ ariaLabel = "Đang tải" }: { ariaLabel?: string }) {
  return (
    <div
      role="status"
      aria-label={ariaLabel}
      className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
    />
  );
}
