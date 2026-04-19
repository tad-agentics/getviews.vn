import { lazy, Suspense } from "react";

const VideoScreen = lazy(() => import("./VideoScreen"));

/**
 * `/app/video` — Phase B · B.1.4 deep-dive (win/flop) backed by Cloud Run
 * `POST /video/analyze`. Query: `?video_id=` or `?url=` (TikTok URL in corpus).
 */
export default function AppVideoRoute() {
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
      <VideoScreen />
    </Suspense>
  );
}
