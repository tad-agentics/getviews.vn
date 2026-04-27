import { useRegisterSW } from "virtual:pwa-register/react";

/**
 * Surfaces a Vietnamese "có bản cập nhật mới" banner when
 * VitePWA's ``registerType: "prompt"`` finds a new service-worker
 * waiting to activate. Tapping "Tải lại" calls
 * ``updateServiceWorker(true)`` which posts ``SKIP_WAITING`` and
 * reloads.
 *
 * Mounted once at the root so every authenticated screen can pick
 * up the banner without each layout having to opt in. The
 * unauthenticated landing also gets the banner — fine; the page
 * is light enough that a reload is cheap.
 */
export function PwaUpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisterError(error) {
      // SW registration failures are non-fatal — log so devs can
      // notice on dashboards but don't surface to the user.
      console.warn("[pwa] register error:", error);
    },
  });

  if (!needRefresh) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 left-4 right-4 z-[60] mx-auto max-w-md rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4 shadow-lg sm:left-auto sm:right-4"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-[color:var(--gv-ink)]">
          Có bản cập nhật mới — tải lại để dùng.
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setNeedRefresh(false)}
            className="rounded-md px-3 py-1.5 text-xs text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)]"
          >
            Để sau
          </button>
          <button
            type="button"
            onClick={() => void updateServiceWorker(true)}
            className="rounded-md bg-[color:var(--gv-accent)] px-3 py-1.5 text-xs font-medium text-white hover:bg-[color:var(--gv-accent-deep)]"
          >
            Tải lại
          </button>
        </div>
      </div>
    </div>
  );
}
