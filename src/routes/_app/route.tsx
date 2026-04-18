import { lazy, Suspense, useEffect } from "react";
import { Navigate, useLocation, useSearchParams } from "react-router";

const HomeScreen = lazy(() => import("./home/HomeScreen"));

/**
 * `/app` — the creator's entry surface (Getviews Studio redesign, A3.3).
 *
 * Routing rules:
 *   - Bare `/app` renders the new HomeScreen.
 *   - `/app?session=<id>` is a legacy chat URL — redirect to
 *     `/app/chat?session=<id>` so bookmarks + HistoryScreen links keep
 *     working.
 */
export default function AppIndexRoute() {
  const [searchParams] = useSearchParams();
  const location = useLocation();

  // Legacy redirect: chat sessions used to live at /app?session=X.
  const session = searchParams.get("session");
  if (session) {
    const q = new URLSearchParams(searchParams);
    return <Navigate to={`/app/chat?${q.toString()}`} replace state={location.state} />;
  }

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
