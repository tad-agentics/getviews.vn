import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { RouteScreenFallback } from "@/components/RouteScreenFallback";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Xu hướng");

/** Shown while the route module / ExploreScreen chunk loads (silences RR dev hint). */
export function HydrateFallback() {
  return <RouteScreenFallback />;
}

const ExploreScreen = lazy(() => import("./ExploreScreen"));

export default function TrendsRoute() {
  return (
    <Suspense fallback={<RouteScreenFallback />}>
      <ExploreScreen />
    </Suspense>
  );
}
