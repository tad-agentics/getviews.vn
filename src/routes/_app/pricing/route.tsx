import { lazy, Suspense } from "react";

const PricingScreen = lazy(() => import("./PricingScreen"));

export default function PricingRoute() {
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
      <PricingScreen />
    </Suspense>
  );
}
