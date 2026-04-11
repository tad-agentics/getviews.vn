/**
 * SSE event union type for the GetViews pipeline stream.
 *
 * The /stream endpoint emits two kinds of tokens:
 *
 *   1. Step events  — {"stream_id":"...", "seq":N, "step": StepEvent}
 *      Emitted before synthesis; drives the AgentStepLogger.
 *
 *   2. Delta tokens — {"stream_id":"...", "seq":N, "delta":"text chunk", "done":false}
 *      Emitted during synthesis streaming.
 *
 *   3. Done token   — {"stream_id":"...", "seq":N, "delta":"", "done":true}
 *
 *   4. Error token  — {"stream_id":"...", "seq":N, "done":true, "error":"code"}
 */

// ---------------------------------------------------------------------------
// Step events (P0-6)
// ---------------------------------------------------------------------------

/** Phase header — shown with rotating spinner, e.g. "Đang tải video..." */
export interface StepStartEvent {
  type: "step_start";
  label: string;
}

/** Search action — Vietnamese query displayed in quotes */
export interface StepSearchEvent {
  type: "step_search";
  source: "tiktok" | "corpus" | "ensemble";
  query: string;
}

/** Creator discovered — purple handle */
export interface StepCreatorEvent {
  type: "step_creator";
  handle: string;
}

/** Count line — "Đã tìm X video" + optional thumbnail previews */
export interface StepCountEvent {
  type: "step_count";
  count: number;
  thumbnails: string[];
}

/** Processing event — secondary spinner, e.g. "Đang phân tích từng video..." */
export interface StepProcessEvent {
  type: "step_process";
  label: string;
}

/** Phase complete — collapses children to "✓" line */
export interface StepDoneEvent {
  type: "step_done";
  summary: string;
}

export type StepEvent =
  | StepStartEvent
  | StepSearchEvent
  | StepCreatorEvent
  | StepCountEvent
  | StepProcessEvent
  | StepDoneEvent;

// ---------------------------------------------------------------------------
// Full SSE token shape
// ---------------------------------------------------------------------------

export interface SseStepToken {
  stream_id?: string;
  seq?: number;
  step: StepEvent;
  done?: false;
  error?: never;
  delta?: never;
}

export interface SseDeltaToken {
  stream_id?: string;
  seq?: number;
  delta: string;
  done: false;
  step?: never;
  error?: never;
}

export interface SseDoneToken {
  stream_id?: string;
  seq?: number;
  delta: string;
  done: true;
  step?: never;
  error?: never;
}

export interface SseErrorToken {
  stream_id?: string;
  seq?: number;
  done: true;
  error: string;
  step?: never;
  delta?: never;
}

export type SseToken = SseStepToken | SseDeltaToken | SseDoneToken | SseErrorToken;

