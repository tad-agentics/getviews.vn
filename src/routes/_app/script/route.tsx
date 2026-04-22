import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Xưởng viết kịch bản");

const ScriptScreen = lazy(() => import("./ScriptScreen"));

/**
 * `/app/script` — Phase B · B.4.3 Xưởng Viết. Query: ``?hook=``, ``?niche_id=``, ``?topic=``, ``?duration=``.
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
