import { lazy, Suspense } from "react";

const CheckoutScreen = lazy(() => import("./CheckoutScreen"));

export default function CheckoutRoute() {
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
      <CheckoutScreen />
    </Suspense>
  );
}
