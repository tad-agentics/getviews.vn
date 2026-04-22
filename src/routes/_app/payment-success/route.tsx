import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Thanh toán thành công");

const PaymentSuccessScreen = lazy(() => import("./PaymentSuccessScreen"));

export default function PaymentSuccessRoute() {
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
      <PaymentSuccessScreen />
    </Suspense>
  );
}
