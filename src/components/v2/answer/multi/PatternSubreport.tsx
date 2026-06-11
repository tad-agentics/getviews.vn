/**
 * Phase C.5.3 — PatternSubreport wrapper.
 *
 * Redesign 2026-05: clock-time / posting-hour subreports are no longer merged
 * into pattern diagnosis. Standalone `format=timing` sessions still use TimingBody.
 */

import type { PatternReportPayload } from "@/lib/api-types";

export function PatternSubreports(_props: { report: PatternReportPayload }) {
  return null;
}
