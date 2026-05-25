import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { Navigate, useLocation, useSearchParams } from "react-router";
import { useProfile } from "@/hooks/useProfile";
import { pageMeta } from "@/lib/pageTitle";
import { profileHasNiche } from "@/lib/profileNiches";
import { studioHomeChannelRedirectPath } from "@/lib/channelStudioHandoff";

export const meta: MetaFunction = () => pageMeta("Sảnh Sáng Tạo");

const HomeScreen = lazy(() => import("./home/HomeScreen"));

/**
 * `/app` — the creator's entry surface (Getviews Studio redesign).
 *
 * Routing rules:
 *   - If the profile has no niche yet (single-niche refactor 2026-05-05),
 *     redirect to `/app/onboarding`.
 *   - Otherwise render HomeScreen.
 */
export default function AppIndexRoute() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { data: profile, isPending } = useProfile();

  const session = searchParams.get("session");
  if (session) {
    return <Navigate to={`/app/answer?session=${encodeURIComponent(session)}`} replace state={location.state} />;
  }

  const scrollTier = searchParams.get("scrollTier");
  const legacyHandle = searchParams.get("handle");
  if (legacyHandle?.trim() && scrollTier) {
    return <Navigate to={`/app?scrollTier=${scrollTier}`} replace state={location.state} />;
  }

  const channelRedirect = studioHomeChannelRedirectPath(searchParams);
  if (channelRedirect && !scrollTier) {
    return <Navigate to={channelRedirect} replace state={location.state} />;
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

  if (profile && !profileHasNiche(profile)) {
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
