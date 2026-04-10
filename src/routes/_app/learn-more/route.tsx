import { lazy, Suspense } from "react";

const LearnMoreScreen = lazy(() => import("./LearnMoreScreen"));

export default function LearnMoreRoute() {
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
      <LearnMoreScreen />
    </Suspense>
  );
}
