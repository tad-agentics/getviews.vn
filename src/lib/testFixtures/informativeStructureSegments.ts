import type { VideoSegment } from "@/lib/api-types";

/** Eight-beat fixture with scene timestamps and enough pct spread for the bar gate. */
export const INFORMATIVE_STRUCTURE_SEGMENTS: VideoSegment[] = [
  { name: "HOOK", pct: 22, color_key: "accent", start_sec: 0, end_sec: 13 },
  { name: "PROMISE", pct: 10, color_key: "ink-2", start_sec: 13, end_sec: 19 },
  { name: "APP 1", pct: 11, color_key: "ink-3", start_sec: 19, end_sec: 26 },
  { name: "APP 2", pct: 11, color_key: "ink-2", start_sec: 26, end_sec: 33 },
  { name: "APP 3", pct: 11, color_key: "ink-3", start_sec: 33, end_sec: 40 },
  { name: "APP 4", pct: 11, color_key: "ink-2", start_sec: 40, end_sec: 47 },
  { name: "APP 5", pct: 12, color_key: "ink-3", start_sec: 47, end_sec: 54 },
  { name: "CTA", pct: 12, color_key: "accent-deep", start_sec: 54, end_sec: 60 },
];
