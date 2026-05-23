import { memo, useCallback, useEffect, useId, useRef, useState } from "react";
import type { NicheWithHot } from "@/hooks/useTopNiches";

/**
 * Studio Home — niche picker pill (PR-5).
 *
 * Sits at the right end of the greeting row. Callers pass the user's niche row(s)
 * (today: one element from ``profileFirstNicheId`` + ``useNicheRowsForIds``).
 *
 * Behaviour:
 *   • Một ngách → chip tĩnh (không dropdown).
 *   • ≥2 rows → nút mở listbox; chọn gọi ``onSelectNiche``; footer mở Cài đặt qua ``onEditNiches``.
 *
 * Không đổi TikTok handle trên profile; chỉ đổi ngách đang ghim cho Home (gợi ý, ticker, pulse, ritual).
 */

export const NichePicker = memo(function NichePicker({
  niches,
  selectedNicheId,
  onSelectNiche,
  onEditNiches,
}: {
  niches: ReadonlyArray<NicheWithHot>;
  selectedNicheId: number | null;
  onSelectNiche: (id: number) => void;
  onEditNiches: () => void;
}) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  const current =
    niches.find((n) => n.id === selectedNicheId) ?? niches[0] ?? null;

  // Close on Escape + on outside click — design opens via the button
  // and dismisses without ceremony, no overlay scrim.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      const target = e.target as Node | null;
      if (!buttonRef.current?.parentElement?.contains(target)) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const handleSelect = useCallback(
    (id: number) => {
      onSelectNiche(id);
      setOpen(false);
      buttonRef.current?.focus();
    },
    [onSelectNiche],
  );

  if (!current) return null;

  // Single-niche profile renders as a static chip (no dropdown).
  if (niches.length <= 1) {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-sm font-medium text-[color:var(--gv-ink)]"
        aria-label="Ngách đang theo dõi"
      >
        <span
          className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--gv-accent)]"
          aria-hidden
        />
        <span className="min-w-0 truncate">{current.name}</span>
      </span>
    );
  }

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={`Ngách đang xem: ${current.name}`}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-2 rounded-full border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] px-3.5 py-2 text-sm font-medium text-[color:var(--gv-ink)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
      >
        <span
          aria-hidden
          className="gv-kicker text-[color:var(--gv-ink-4)]"
        >
          NGÁCH
        </span>
        <span>{current.name}</span>
        {current.hot > 0 ? (
          <span className="gv-kicker text-[color:var(--gv-pos-deep)]">
            ↑{current.hot} hot
          </span>
        ) : null}
      </button>
      {open ? (
        <div
          id={panelId}
          role="listbox"
          aria-label="Chọn ngách"
          className="absolute right-0 top-[calc(100%+6px)] z-20 min-w-[240px] rounded-lg border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] p-1.5 shadow-[0_12px_32px_-12px_rgba(0,0,0,0.2)]"
        >
          {niches.map((n) => {
            const isCurrent = n.id === current.id;
            return (
              <button
                key={n.id}
                type="button"
                role="option"
                aria-selected={isCurrent}
                onClick={() => handleSelect(n.id)}
                className={
                  "flex w-full items-center justify-between gap-2 rounded-md px-2.5 py-2 text-left text-sm text-[color:var(--gv-ink)] transition-colors hover:bg-[color:var(--gv-canvas-2)] " +
                  (isCurrent ? "bg-[color:var(--gv-canvas-2)]" : "")
                }
              >
                <span>{n.name}</span>
                <span className="gv-kicker text-[color:var(--gv-ink-4)]">
                  {n.hot.toLocaleString("vi-VN")}
                </span>
              </button>
            );
          })}
          <div className="mt-1 border-t border-[color:var(--gv-rule)] pt-1">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                onEditNiches();
              }}
              className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left gv-kicker text-[color:var(--gv-ink-3)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
            >
              + Đổi ngách đang theo dõi
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
});
