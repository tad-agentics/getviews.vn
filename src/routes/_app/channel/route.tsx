import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Soi kênh");

const ChannelScreen = lazy(() => import("./ChannelScreen"));

/** `/app/channel` — channel intelligence full page (composer pill Khám Kênh). */
export default function AppChannelRoute() {
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
      <ChannelScreen />
    </Suspense>
  );
}
