import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("So sánh hai video");

const CompareScreen = lazy(() => import("./CompareScreen"));

/**
 * `/app/compare` — Wave 4 PR #3 entry. Two TikTok URLs in one query
 * arrive here as ``?url_a=`` + ``?url_b=`` (the FE intent router's
 * compare branch), then we POST to Cloud Run /stream with intent
 * ``compare_videos``. The server orchestrates parallel diagnoses +
 * delta synthesis (see ``cloud-run/getviews_pipeline/report_compare``)
 * and returns a ``ComparePayload`` that ``CompareBody`` renders.
 */
export default function AppCompareRoute() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          aria-label="Đang tải so sánh"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
        />
      }
    >
      <CompareScreen />
    </Suspense>
  );
}
