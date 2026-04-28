import { formatRelativeSinceVi } from "@/lib/formatters";

/**
 * TopBar chip: corpus / pulse freshness from ``/home/pulse`` ``as_of``.
 * Hidden below `md` (`hide-narrow`) to match Channel / Trends / Video.
 */
export function DataFreshnessPill({ asOfIso }: { asOfIso: string | null | undefined }) {
  if (!asOfIso) return null;
  const d = new Date(asOfIso);
  if (Number.isNaN(d.getTime())) return null;
  const rel = formatRelativeSinceVi(new Date(), d);
  if (rel === "—") return null;

  return (
    <span className="hide-narrow hidden items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)] md:inline-flex">
      <span
        className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--gv-accent)]"
        style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
      />
      Dữ liệu cập nhật {rel}
    </span>
  );
}
