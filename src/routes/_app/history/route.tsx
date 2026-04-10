import { lazy, Suspense } from "react";

const HistoryScreen = lazy(() => import("./HistoryScreen"));

export default function HistoryRoute() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[var(--surface-alt)]"
        />
      }
    >
      <HistoryScreen />
    </Suspense>
  );
}
