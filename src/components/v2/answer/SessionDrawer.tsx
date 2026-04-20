import { X, Sparkles } from "lucide-react";
import type { AnswerSessionRow } from "@/lib/api-types";

function relTime(iso: string | undefined): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const d = Math.floor((Date.now() - t) / 86_400_000);
  if (d <= 0) return "Hôm nay";
  if (d === 1) return "Hôm qua";
  if (d < 7) return `${d} ngày`;
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
}

/** Phase C.1.3 — recent answer sessions (thread-turns.jsx drawer pattern). */
export function SessionDrawer({
  open,
  onClose,
  sessions,
  activeSessionId,
  onSelect,
  onNewSession,
  onViewAll,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  sessions: AnswerSessionRow[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewSession: () => void;
  onViewAll: () => void;
  isLoading: boolean;
}) {
  if (!open) return null;
  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-[100] bg-[color:var(--gv-scrim)]"
        aria-label="Đóng"
        onClick={onClose}
      />
      <div
        className="fixed left-0 top-0 z-[101] flex h-full w-[min(380px,100vw)] flex-col border-r border-[var(--gv-ink)] bg-[var(--gv-canvas)] shadow-lg animate-in slide-in-from-left duration-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="answer-drawer-title"
      >
        <div className="border-b border-[var(--gv-rule)] px-5 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--gv-ink-4)]">
            Phiên nghiên cứu
          </p>
          <div className="mt-1 flex items-start justify-between gap-2">
            <h2 id="answer-drawer-title" className="gv-serif text-[22px] font-medium text-[var(--gv-ink)]">
              Các phiên gần đây
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-[var(--gv-rule)] p-1.5 text-[var(--gv-ink-2)] hover:bg-[var(--gv-canvas-2)]"
              aria-label="Đóng"
            >
              <X className="size-4" />
            </button>
          </div>
          <button
            type="button"
            onClick={() => {
              onNewSession();
              onClose();
            }}
            className="btn btn-accent mt-4 flex w-full items-center justify-center gap-2 py-3 text-[15px]"
          >
            <Sparkles className="size-4" />
            Phiên mới
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {isLoading ? (
            <p className="px-3 py-4 text-sm text-[var(--gv-ink-3)]">Đang tải…</p>
          ) : sessions.length === 0 ? (
            <p className="px-3 py-4 text-sm text-[var(--gv-ink-3)]">Chưa có phiên nào.</p>
          ) : (
            <ul className="space-y-1">
              {sessions.map((s) => {
                const active = s.id === activeSessionId;
                return (
                  <li key={s.id}>
                    <button
                      type="button"
                      onClick={() => {
                        onSelect(s.id);
                        onClose();
                      }}
                      className={`w-full rounded-md px-3 py-3 text-left transition-colors ${
                        active
                          ? "border-l-[3px] border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)]"
                          : "border-l-[3px] border-transparent hover:bg-[var(--gv-canvas-2)]"
                      }`}
                    >
                      <p className="font-mono text-[9px] uppercase tracking-wide text-[var(--gv-ink-4)]">
                        {relTime(s.updated_at)}
                      </p>
                      <p className="mt-0.5 line-clamp-2 text-[14px] leading-snug text-[var(--gv-ink)]">
                        {s.title?.trim() || s.initial_q?.slice(0, 120) || "Phiên nghiên cứu"}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <div className="border-t border-[var(--gv-rule)] px-4 py-3">
          <button
            type="button"
            onClick={() => {
              onClose();
              onViewAll();
            }}
            className="font-mono text-[12px] text-[color:var(--gv-accent)] hover:underline"
          >
            Xem tất cả →
          </button>
        </div>
      </div>
    </>
  );
}
