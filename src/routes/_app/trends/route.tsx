import { lazy, Suspense } from "react";

const ExploreScreen = lazy(() => import("./ExploreScreen"));

export default function TrendsRoute() {
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
      <ExploreScreen />
    </Suspense>
  );
}
