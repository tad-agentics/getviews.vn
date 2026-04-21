import { lazy, Suspense } from "react";

const ShootScreen = lazy(() => import("./ShootScreen"));

/**
 * `/app/script/shoot/:draftId` — Phase D · D.1.1 "Chế độ quay".
 * Read-only mobile-friendly view of a saved draft. Lazy-loaded to keep
 * ScriptScreen's critical path small.
 */
export default function AppScriptShootRoute() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          aria-label="Đang tải chế độ quay"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
        />
      }
    >
      <ShootScreen />
    </Suspense>
  );
}
