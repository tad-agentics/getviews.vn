import { lazy, Suspense } from "react";

const HomeScreen = lazy(() => import("./HomeScreen"));

export default function HomeRoute() {
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
      <HomeScreen />
    </Suspense>
  );
}
