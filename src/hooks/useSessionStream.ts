/**
 * Phase C.1.0 — shared SSE stream + credit semantics for chat and `/answer`.
 * Same implementation as `useChatStream`; alias exists so `/answer` and future
 * surfaces import a neutral name per phase-c-plan.md.
 */
export { useChatStream as useSessionStream } from "./useChatStream";
export type { StreamState, StreamStatus } from "./useChatStream";
