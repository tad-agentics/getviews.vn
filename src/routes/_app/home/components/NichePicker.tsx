import { memo, useEffect, useRef, useState } from "react";
import { useProfile } from "@/hooks/useProfile";
import { useTopNiches } from "@/hooks/useTopNiches";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";

/**
 * Greeting-row inline niche picker. Matches the design's `NichePicker` —
 * an ink-bordered pill that opens a popover of niches the user can pick
 * between. Selecting a niche writes `profiles.primary_niche`; the whole
 * Home screen re-runs off that.
 *
 * Picker list reuses `useTopNiches`, which floats the current niche to
 * the top; fine as the current shape since we only have 1 "tracked".
 */
export const NichePicker = memo(function NichePicker() {
  const { data: profile } = useProfile();
  const { data: niches = [] } = useTopNiches(profile?.primary_niche ?? null, 12);
  const save = useUpdateProfile();
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement | null>(null);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (popRef.current && !popRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const current = niches.find((n) => n.id === profile?.primary_niche);

  if (niches.length === 0) return null;

  return (
    <div className="relative" ref={popRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-3 rounded-full border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] px-4 py-2.5 transition-colors hover:bg-[color:var(--gv-canvas-2)]"
      >
        <span className="gv-mono text-[9px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
          Ngách
        </span>
        <span className="text-sm font-medium text-[color:var(--gv-ink)]">
          {current?.name ?? "Chọn ngách"}
        </span>
        {current ? (
          <span className="gv-mono text-[10px] text-[color:var(--gv-accent-deep)]">
            ↓ {current.hot} hot
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute left-0 top-[calc(100%+6px)] z-20 min-w-[260px] rounded-[8px] border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] shadow-[0_12px_32px_-12px_rgba(0,0,0,0.2)]">
          <ul className="max-h-[320px] overflow-y-auto py-1">
            {niches.map((n) => {
              const active = n.id === profile?.primary_niche;
              return (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={async () => {
                      if (n.id !== profile?.primary_niche) {
                        await save.mutateAsync({ primary_niche: n.id });
                      }
                      setOpen(false);
                    }}
                    className={
                      "flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-[13px] transition-colors " +
                      (active
                        ? "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink)]"
                        : "text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)]")
                    }
                  >
                    <span className="truncate">{n.name}</span>
                    <span className="gv-mono text-[10px] text-[color:var(--gv-pos-deep)] shrink-0">
                      ↑ {n.hot}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
});
