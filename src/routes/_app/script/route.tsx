import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Phân tích");

const ScriptScreen = lazy(() => import("./ScriptScreen"));

/**
 * Wave 2 — legacy shim. ``/app/script`` redirects to ``/app/answer`` with
 * composer ``?q=`` prefill (see ``scriptRouteRedirectPath``).
 */
export default function AppScriptRoute() {
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
      <ScriptScreen />
    </Suspense>
  );
}
