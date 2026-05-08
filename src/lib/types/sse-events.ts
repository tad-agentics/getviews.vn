/**
 * SSE step event types — mirrors cloud-run/getviews_pipeline/step_events.py.
 * These are emitted during pipeline execution and consumed by LivePipelineStrip.
 *
 * Lightreel parity: tool_start/tool_complete carry iteration + index so
 * the FE can render parallel tool cards that complete out-of-order.
 */

export type StepToolName =
  | "corpus"
  | "tiktok_live"
  | "synthesis"
  | "creator_posts"
  | "search";

export interface StepStatus {
  type: "step_status";
  iteration: number;
  text: string;
}

export interface StepToolStart {
  type: "step_tool_start";
  label: string;
  iteration: number;
  index: number;
  tool: StepToolName;
}

export interface StepToolComplete {
  type: "step_tool_complete";
  iteration: number;
  index: number;
  /** Awemes returned to the synthesis prompt (post-filter). */
  found: number;
  thumbnails: string[]; // max 5 URLs
  tool: StepToolName;
  /** Awemes the tool fetched but discarded (e.g., news-aggregator
   *  blocklist). Optional — only emitted when > 0. The FE can render
   *  "Tìm thấy N · lọc M" so users see the difference between
   *  "search returned nothing" and "search returned only filtered
   *  results". */
  filtered?: number;
}

// Legacy sequential events (still emitted by some builders)
export interface StepStart {
  type: "step_start";
  label: string;
}
export interface StepSearch {
  type: "step_search";
  // Matches step_events.py docstring — pipelines emit "corpus" |
  // "ensemble" | "tiktok" in practice. Kept as `string` for forward
  // compat (BE may add more sources without an FE type bump).
  source: string;
  query: string;
}
export interface StepCreator {
  type: "step_creator";
  handle: string;
}
export interface StepCount {
  type: "step_count";
  count: number;
  thumbnails: string[];
}
export interface StepProcess {
  type: "step_process";
  label: string;
}
export interface StepDone {
  type: "step_done";
  summary: string;
}
export interface StepError {
  type: "step_error";
  code: string;
  message_vi: string;
}

export type StepEvent =
  | StepStatus
  | StepToolStart
  | StepToolComplete
  | StepStart
  | StepSearch
  | StepCreator
  | StepCount
  | StepProcess
  | StepDone
  | StepError;

export const STEP_EVENT_TYPES = new Set<string>([
  "step_status",
  "step_tool_start",
  "step_tool_complete",
  "step_start",
  "step_search",
  "step_creator",
  "step_count",
  "step_process",
  "step_done",
  "step_error",
]);
