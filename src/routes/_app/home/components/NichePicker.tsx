import { memo, useEffect, useRef, useState } from "react";
import { useProfile } from "@/hooks/useProfile";
import { useTopNiches } from "@/hooks/useTopNiches";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";

/**
 * Greeting-row niche picker — UIUX `home.jsx` NichePicker:
 * `padding: 10px 16px`, `gap: 8`, `1px solid var(--ink)`, pill radius,
 * paper bg, label `NGÁCH` mono 9px ink-4, value 13px medium, hot line 12px accent-deep.
 * Popover: `right: 0`, `top: calc(100% + 6px)`, ink border, 8px radius, 6px padding shell.
 */
export const NichePicker = memo(function NichePicker() {
  const { data: profile } = useProfile();
  const { data: niches = [] } = useTopNiches(profile?.primary_niche ?? null, 12);
  const save = useUpdateProfile();
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement | null>(null);

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
        className="inline-flex items-center gap-2 rounded-full border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] px-4 py-2.5 text-[13px] font-medium text-[color:var(--gv-ink)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
      >
        <span className="gv-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          NGÁCH
        </span>
        <span>{current?.name ?? "Chọn ngách"}</span>
        {current ? (
          <span className="gv-mono text-[12px] font-medium text-[color:var(--gv-accent-deep)]">
            ↓ {current.hot} hot
          </span>
        ) : null}
      </button>

      {open ? (
        <>
          <div className="fixed inset-0 z-[20]" aria-hidden onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-[calc(100%+6px)] z-[30] min-w-[240px] rounded-[8px] border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] p-1.5 shadow-[0_12px_32px_-12px_rgba(0,0,0,0.2)]">
            <ul className="max-h-[320px] overflow-y-auto">
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
                        "flex w-full items-center justify-between gap-3 rounded-[6px] px-2.5 py-2 text-left text-[13px] transition-colors " +
                        (active
                          ? "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink)]"
                          : "text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)]")
                      }
                    >
                      <span className="truncate">{n.name}</span>
                      <span className="gv-mono shrink-0 text-[10px] text-[color:var(--gv-ink-4)]">
                        {n.hot.toLocaleString("vi-VN")}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </>
      ) : null}
    </div>
  );
});
