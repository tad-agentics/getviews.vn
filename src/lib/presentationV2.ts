import { env } from "@/lib/env";

/** Gate Part A FE presentation upgrades (retention chart, hook strip, etc.). */
export function isReportPresentationV2(): boolean {
  return env.VITE_REPORT_PRESENTATION_V2 === true;
}
