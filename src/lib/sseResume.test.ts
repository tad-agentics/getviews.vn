/**
 * Resume-on-reload guard for the answer-turn SSE.
 *
 * Cloud Run's replay buffer has a 60s TTL
 * (cloud-run/getviews_pipeline/session_store.py:40 _STREAM_REPLAY_TTL_SEC).
 * The client's RESUME_MAX_AGE_MS cap sits 15s below that to absorb
 * clock drift. These tests lock in that margin — if someone bumps
 * the constant above the server TTL, a stale entry could trigger an
 * auto-resume that misses the buffer and falls through to fresh
 * Gemini.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  clearPendingAnswerStream,
  hasAnswerStreamReplayHandles,
  loadPendingAnswerStream,
  optimisticAnswerCreditsUsed,
  PENDING_ANSWER_STREAM_KEY,
  PENDING_ANSWER_STREAM_MAX_AGE_MS,
  savePendingAnswerStream,
} from "./sseResume";

const EPOCH = 1_800_000_000_000;

function makeEntry(
  overrides: Partial<{
    sessionId: string;
    streamId: string;
    seq: number;
    startedAt: number;
    creditsUsed: number;
    sessionFormat: string | null;
  }> = {},
) {
  const creditsUsed = overrides.creditsUsed ?? 1;
  const sessionFormat = overrides.sessionFormat;
  return {
    sessionId: overrides.sessionId ?? "sess-1",
    streamId: overrides.streamId ?? "stream-abc",
    seq: overrides.seq ?? 2,
    query: "Ngách tai nghe đang bật gì?",
    turnKind: "primary" as const,
    startedAt: overrides.startedAt ?? EPOCH,
    creditsUsed,
    ...(sessionFormat !== undefined ? { sessionFormat } : {}),
  };
}

describe("sseResume", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it("round-trips save → load for a fresh entry", () => {
    savePendingAnswerStream({ ...makeEntry(), videoMode: "flop" });
    const loaded = loadPendingAnswerStream("sess-1", EPOCH + 10_000);
    expect(loaded?.streamId).toBe("stream-abc");
    expect(loaded?.seq).toBe(2);
    expect(loaded?.creditsUsed).toBe(1);
    expect(loaded?.videoMode).toBe("flop");
  });

  it("hasAnswerStreamReplayHandles is true for pending or hook seq", () => {
    savePendingAnswerStream(makeEntry());
    expect(hasAnswerStreamReplayHandles("sess-1", null, 0, EPOCH + 1000)).toBe(true);
    expect(hasAnswerStreamReplayHandles("sess-1", "sid", 1, EPOCH + 1000)).toBe(true);
    expect(hasAnswerStreamReplayHandles("sess-2", null, 0, EPOCH)).toBe(false);
  });

  it("infers creditsUsed=2 for legacy primary + video format + deep when creditsUsed omitted", () => {
    const legacy = {
      sessionId: "sess-1",
      streamId: "stream-abc",
      seq: 2,
      query: "Phân tích video",
      turnKind: "primary" as const,
      startedAt: EPOCH,
      sessionFormat: "video" as const,
    };
    sessionStorage.setItem(PENDING_ANSWER_STREAM_KEY, JSON.stringify(legacy));
    const loaded = loadPendingAnswerStream("sess-1", EPOCH + 10_000);
    expect(loaded?.creditsUsed).toBe(2);
  });

  it("infers creditsUsed=3 for legacy primary + script format when creditsUsed omitted", () => {
    const legacy = {
      sessionId: "sess-1",
      streamId: "stream-abc",
      seq: 2,
      query: "Viết kịch bản",
      turnKind: "primary" as const,
      startedAt: EPOCH,
      sessionFormat: "script" as const,
    };
    sessionStorage.setItem(PENDING_ANSWER_STREAM_KEY, JSON.stringify(legacy));
    const loaded = loadPendingAnswerStream("sess-1", EPOCH + 10_000);
    expect(loaded?.creditsUsed).toBe(3);
  });

  it("returns null when the stored session doesn't match the current one", () => {
    savePendingAnswerStream(makeEntry({ sessionId: "other" }));
    expect(loadPendingAnswerStream("sess-1", EPOCH)).toBeNull();
  });

  it("returns null and drops the entry when older than the TTL margin", () => {
    savePendingAnswerStream(makeEntry({ startedAt: EPOCH }));
    const loaded = loadPendingAnswerStream(
      "sess-1",
      EPOCH + PENDING_ANSWER_STREAM_MAX_AGE_MS + 1,
    );
    expect(loaded).toBeNull();
    // Side-effect: stale entry is evicted so subsequent reads don't
    // re-parse it.
    expect(sessionStorage.getItem(PENDING_ANSWER_STREAM_KEY)).toBeNull();
  });

  it("returns null when the entry has no streamId / seq yet (pre-first-token)", () => {
    savePendingAnswerStream(makeEntry({ streamId: "", seq: 0 }));
    expect(loadPendingAnswerStream("sess-1", EPOCH)).toBeNull();
  });

  it("clearPendingAnswerStream removes any stored entry", () => {
    savePendingAnswerStream(makeEntry());
    clearPendingAnswerStream();
    expect(sessionStorage.getItem(PENDING_ANSWER_STREAM_KEY)).toBeNull();
  });

  it("handles malformed JSON by evicting the entry", () => {
    sessionStorage.setItem(PENDING_ANSWER_STREAM_KEY, "{not json");
    expect(loadPendingAnswerStream("sess-1", EPOCH)).toBeNull();
    expect(sessionStorage.getItem(PENDING_ANSWER_STREAM_KEY)).toBeNull();
  });

  it("TTL margin stays safely under Cloud Run's 60s replay buffer", () => {
    // Regression guard — the server-side buffer is 60s
    // (cloud-run/getviews_pipeline/session_store.py:40
    // _STREAM_REPLAY_TTL_SEC). Leaving ≥15s slack absorbs clock drift +
    // trip-time so the auto-resume path does not miss the buffer.
    expect(PENDING_ANSWER_STREAM_MAX_AGE_MS).toBeLessThanOrEqual(60_000 - 15_000);
  });

  it("optimisticAnswerCreditsUsed mirrors append_turn billing", () => {
    expect(optimisticAnswerCreditsUsed("script")).toBe(3);
    expect(optimisticAnswerCreditsUsed("primary", "script")).toBe(3);
    expect(optimisticAnswerCreditsUsed("primary", "video")).toBe(2);
    expect(optimisticAnswerCreditsUsed("primary", "pattern")).toBe(1);
    expect(optimisticAnswerCreditsUsed("timing")).toBe(0);
  });
});
