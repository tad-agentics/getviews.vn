import { useCallback, useEffect, useRef, useState } from "react";
import type { FindingEvidenceRef } from "@/lib/api-types";

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

/** Caption under the inline clip — range + optional moment label. */
export function evidenceCaptionLabel(ref: FindingEvidenceRef): string {
  const rangeLabel = evidenceRangeLabel(ref);
  const moment = ref.label_vi?.trim();
  if (rangeLabel && moment) return `${rangeLabel} · ${moment}`;
  if (rangeLabel) return rangeLabel;
  if (moment) return moment;
  return "Đoạn trong clip";
}

/** Returns the playable start time, or null when the ref has no usable timestamp. */
export function resolveStartSec(ref: FindingEvidenceRef): number | null {
  if (ref.start_sec != null && Number.isFinite(ref.start_sec) && ref.start_sec >= 0) {
    return ref.start_sec;
  }
  if (ref.end_sec != null && Number.isFinite(ref.end_sec) && ref.end_sec > 0) {
    return Math.max(0, ref.end_sec - 2);
  }
  return null;
}

function resolveEndSec(ref: FindingEvidenceRef, startSec: number): number | null {
  const end = ref.end_sec;
  if (end == null || !Number.isFinite(end) || end <= startSec) return null;
  return end;
}

/**
 * Inline 9:16 clip from the analyzed video, seeked to the moment that proves a
 * finding. Renders nothing when there is no clip URL or no usable timestamp.
 */
export function FindingEvidenceClip({
  evidenceRef,
  clip,
}: {
  evidenceRef: FindingEvidenceRef | null | undefined;
  clip: AnalyzedClipContext | null | undefined;
}) {
  if (!evidenceRef || !clip?.clipUrl) return null;
  const startSec = resolveStartSec(evidenceRef);
  if (startSec == null) return null;

  return (
    <FindingEvidenceClipPlayer
      clipUrl={clip.clipUrl}
      startSec={startSec}
      endSec={resolveEndSec(evidenceRef, startSec)}
      caption={evidenceCaptionLabel(evidenceRef)}
    />
  );
}

function FindingEvidenceClipPlayer({
  clipUrl,
  startSec,
  endSec,
  caption,
}: {
  clipUrl: string;
  startSec: number;
  endSec: number | null;
  caption: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hoverPlaying, setHoverPlaying] = useState(false);

  const seekToStart = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    try {
      el.currentTime = startSec;
    } catch {
      // metadata not ready
    }
  }, [startSec]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    el.addEventListener("loadedmetadata", seekToStart, { once: true });
    return () => el.removeEventListener("loadedmetadata", seekToStart);
  }, [clipUrl, seekToStart]);

  useEffect(() => {
    if (endSec == null || !hoverPlaying) return;
    const el = videoRef.current;
    if (!el) return;
    const onTimeUpdate = () => {
      if (el.currentTime >= endSec) {
        seekToStart();
      }
    };
    el.addEventListener("timeupdate", onTimeUpdate);
    return () => el.removeEventListener("timeupdate", onTimeUpdate);
  }, [clipUrl, endSec, hoverPlaying, seekToStart]);

  const startHoverClip = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    seekToStart();
    void el.play().catch(() => {});
    setHoverPlaying(true);
  }, [seekToStart]);

  const stopHoverClip = useCallback(() => {
    setHoverPlaying(false);
    const el = videoRef.current;
    if (!el) return;
    el.pause();
    seekToStart();
  }, [seekToStart]);

  return (
    <figure className="mt-3 max-w-[168px]">
      <div
        className="relative overflow-hidden rounded-lg border border-[color:var(--gv-rule)] bg-black"
        style={{ aspectRatio: "9/16" }}
        onMouseEnter={startHoverClip}
        onMouseLeave={stopHoverClip}
      >
        <video
          ref={videoRef}
          src={clipUrl}
          muted
          loop={endSec == null}
          playsInline
          preload="metadata"
          className="h-full w-full object-cover"
          aria-label={caption}
          data-start-sec={startSec}
        />
      </div>
      <figcaption className="mt-1.5 gv-mono text-[11px] leading-snug text-[color:var(--gv-ink-2)]">
        {caption}
      </figcaption>
    </figure>
  );
}
