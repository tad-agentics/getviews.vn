export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 ${className}`}
    >
      <div className="mb-3 h-4 w-2/3 rounded bg-[var(--surface-alt)]" />
      <div className="mb-2 h-3 w-full rounded bg-[var(--surface-alt)]" />
      <div className="h-3 w-5/6 rounded bg-[var(--surface-alt)]" />
    </div>
  );
}
