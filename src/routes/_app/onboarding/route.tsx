import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Thiết lập ban đầu");

const OnboardingScreen = lazy(() => import("./OnboardingScreen"));

/**
 * `/app/onboarding` — creator onboarding (Phase A · A3.5).
 * Rendered full-bleed (NOT inside AppLayout), matching the design bundle's
 * split-screen editorial layout.
 */
export default function OnboardingRoute() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
        />
      }
    >
      <OnboardingScreen />
    </Suspense>
  );
}
