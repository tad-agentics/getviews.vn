import { lazy, Suspense } from "react";

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
