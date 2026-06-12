import { lazy, Suspense, useState } from "react";
import { Play } from "lucide-react";
import type { ExploreGridVideo } from "@/components/explore/VideoPlayerModal";
import type { FindingEvidenceRef } from "@/lib/api-types";

const VideoPlayerModal = lazy(() =>
  import("@/components/explore/VideoPlayerModal").then((m) => ({
    default: m.VideoPlayerModal,
  })),
);

/** Context needed to deep-link a finding to a moment in the analyzed clip. */
export interface AnalyzedClipContext {
  videoId: string;
  /** R2-hosted MP4 of the analyzed video — null when not banked yet. */
  clipUrl: string | null;
  durationSec: number;
}

function fmtSec(sec: number): string {
  if (!Number.isFinite(sec)) return "";
  if (sec >= 60) {
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  }
  // One decimal only when sub-second precision is meaningful.
  return Number.isInteger(sec) ? `${sec}s` : `${sec.toFixed(1)}s`;
}

/** Human range label: "0–3s", "0:12–0:18", or single point "3.2s". */
export function evidenceRangeLabel(ref: FindingEvidenceRef): string {
  const start = ref.start_sec;
  const end = ref.end_sec;
  if (start != null && end != null && end > start) {
    // Both sub-minute → share the trailing unit: "0–3s".
    if (start < 60 && end < 60) {
      const a = Number.isInteger(start) ? `${start}` : start.toFixed(1);
      const b = Number.isInteger(end) ? `${end}` : end.toFixed(1);
      return `${a}–${b}s`;
    }
    return `${fmtSec(start)}–${fmtSec(end)}`;
  }
  if (start != null) return fmtSec(start);
  if (end != null) return fmtSec(end);
  return "";
}

/** Returns the playable start time, or null when the ref has no usable timestamp. */
function resolveStartSec(ref: FindingEvidenceRef): number | null {
  if (ref.start_sec != null && Number.isFinite(ref.start_sec) && ref.start_sec >= 0) {
    return ref.start_sec;
  }
  if (ref.end_sec != null && Number.isFinite(ref.end_sec) && ref.end_sec > 0) {
    return Math.max(0, ref.end_sec - 2);
  }
  return null;
}

/**
 * "▶ Xem N–Ms trong clip" — plays the analyzed video's own R2 clip seeked to
 * the moment that proves a finding. Renders nothing when there is no clip URL
 * or no usable timestamp (so strengths still degrade to text-only cards).
 */
export function FindingEvidenceClip({
  evidenceRef,
  clip,
}: {
  evidenceRef: FindingEvidenceRef | null | undefined;
  clip: AnalyzedClipContext | null | undefined;
}) {
  const [open, setOpen] = useState(false);

  if (!evidenceRef || !clip?.clipUrl) return null;
  const startSec = resolveStartSec(evidenceRef);
  if (startSec == null) return null;

  const rangeLabel = evidenceRangeLabel(evidenceRef);
  const moment = evidenceRef.label_vi?.trim();
  const buttonLabel = rangeLabel
    ? `Xem ${rangeLabel} trong clip${moment ? ` · ${moment}` : ""}`
    : "Xem đoạn này trong clip";

  const playerVideo: ExploreGridVideo = {
    id: clip.videoId,
    video_id: clip.videoId,
    views: "",
    time: "",
    img: "",
    text: moment ?? "",
    handle: "",
    caption: moment ?? "",
    likes: "",
    comments: "",
    shares: "",
    videoUrl: clip.clipUrl,
    tiktok_url: null,
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-[color:var(--gv-pos)]/30 bg-[color:var(--gv-pos)]/8 px-3 py-1.5 text-[13px] font-medium text-[color:var(--gv-ink)] transition-colors hover:border-[color:var(--gv-pos)]/55"
      >
        <Play className="h-3.5 w-3.5 shrink-0 text-[color:var(--gv-pos)]" fill="currentColor" />
        <span>{buttonLabel}</span>
      </button>
      {open ? (
        <Suspense fallback={null}>
          <VideoPlayerModal
            video={playerVideo}
            allVideos={[playerVideo]}
            startSec={startSec}
            onClose={() => setOpen(false)}
          />
        </Suspense>
      ) : null}
    </>
  );
}
