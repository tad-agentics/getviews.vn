import { lazy, Suspense } from "react";
import { Navigate, useLocation, useSearchParams } from "react-router";
import { useProfile } from "@/hooks/useProfile";

const HomeScreen = lazy(() => import("./home/HomeScreen"));

/**
 * `/app` — the creator's entry surface (Getviews Studio redesign).
 *
 * Routing rules:
 *   - `/app?session=<id>` redirects to `/app/chat?session=<id>` (legacy
 *     chat URLs).
 *   - If the profile has no primary_niche yet, redirect to
 *     `/app/onboarding` so the creator sees the full-bleed onboarding
 *     instead of a half-empty Home.
 *   - Otherwise render HomeScreen.
 */
export default function AppIndexRoute() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { data: profile, isPending } = useProfile();

  const session = searchParams.get("session");
  if (session) {
    const q = new URLSearchParams(searchParams);
    return <Navigate to={`/app/chat?${q.toString()}`} replace state={location.state} />;
  }

  // Wait for the profile query to resolve before deciding. This avoids a
  // flicker from Home → Onboarding on the very first render for new users.
  if (isPending) {
    return (
      <div
        role="status"
        aria-label="Đang tải"
        className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
      />
    );
  }

  if (profile && !profile.primary_niche) {
    return <Navigate to="/app/onboarding" replace />;
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
