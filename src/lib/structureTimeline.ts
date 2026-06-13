import type { VideoSegment } from "@/lib/api-types";

/** Canonical eight-beat labels from ``video_structural.decompose_segments``. */
const BEAT_NAME_VI: Record<string, string> = {
  HOOK: "Hook",
  PROMISE: "Lời hứa",
  "APP 1": "Lý do 1",
  "APP 2": "Lý do 2",
  "APP 3": "Lý do 3",
  "APP 4": "Lý do 4",
  "APP 5": "Lý do 5",
  CTA: "Kêu gọi",
};

export function structureBeatLabelVi(name: string): string {
  const trimmed = name.trim();
  return BEAT_NAME_VI[trimmed.toUpperCase()] ?? trimmed;
}

function formatClockSec(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  if (s >= 60) {
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }
  return `${s}s`;
}

export function formatStructureTimeRange(startSec: number, endSec: number): string {
  const lo = Math.min(startSec, endSec);
  const hi = Math.max(startSec, endSec);
  if (Math.abs(hi - lo) < 0.05) return formatClockSec(lo);
  return `${formatClockSec(lo)}–${formatClockSec(hi)}`;
}

/** Template/fallback bars have pct only — no scene timestamps. */
export function segmentsHaveSceneTimestamps(segments: VideoSegment[]): boolean {
  return segments.some(
    (s) =>
      s.start_sec != null &&
      s.end_sec != null &&
      Number.isFinite(s.start_sec) &&
      Number.isFinite(s.end_sec) &&
      s.end_sec > s.start_sec,
  );
}

/** Hide bars that look like noise: equal buckets or non-scene template. */
export function isInformativeStructureTimeline(segments: VideoSegment[]): boolean {
  if (segments.length < 2) return false;
  if (!segmentsHaveSceneTimestamps(segments)) return false;
  const pcts = segments.map((s) => s.pct);
  return Math.max(...pcts) - Math.min(...pcts) >= 5;
}

export function buildStructureTimelineSummary(
  segments: VideoSegment[],
  durationSec: number,
): string {
  const dur = Math.max(1, Math.round(durationSec));
  const hook = segments[0];
  const hookEnd =
    hook?.end_sec != null && Number.isFinite(hook.end_sec)
      ? hook.end_sec
      : (hook?.pct ?? 0) * 0.01 * dur;
  const hookPct = hook?.pct ?? 0;
  const bodyPcts = segments.slice(1, -1).map((s) => s.pct);
  const bodyAvg =
    bodyPcts.length > 0
      ? Math.round(bodyPcts.reduce((a, b) => a + b, 0) / bodyPcts.length)
      : 0;

  if (hookPct >= 18) {
    return `Hook kéo dài ~${formatClockSec(hookEnd)} (${hookPct}% clip) — phần thân ${bodyPcts.length} nhịp chiếm phần còn lại.`;
  }
  if (hookPct <= 8 && bodyAvg >= 12) {
    return `Hook gọn ~${formatClockSec(hookEnd)}; phần lớn ${dur}s dành cho ${bodyPcts.length} nhịp lý do + kêu gọi cuối.`;
  }
  return `${segments.length} nhịp trong ${dur}s — mỗi ô là khoảng thời gian thực từ cắt cảnh, không phải retention.`;
}
