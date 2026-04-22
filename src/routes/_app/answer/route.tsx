import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Nghiên cứu");

const AnswerScreen = lazy(() => import("./AnswerScreen"));

/** `/app/answer` — research shell (Phase C.1). */
export default function AppAnswerRoute() {
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
      <AnswerScreen />
    </Suspense>
  );
}
