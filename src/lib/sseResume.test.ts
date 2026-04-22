/**
 * Resume-on-reload guard for the answer-turn SSE.
 *
 * Cloud Run's replay buffer has a 120s TTL; the client's
 * RESUME_MAX_AGE_MS cap sits 30s below that to absorb clock drift.
 * These tests lock in that margin — if someone bumps the constant
 * above the server TTL, a stale entry could trigger an auto-resume
 * that misses the buffer and re-bills the user's credits.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  clearPendingAnswerStream,
  loadPendingAnswerStream,
  PENDING_ANSWER_STREAM_KEY,
  PENDING_ANSWER_STREAM_MAX_AGE_MS,
  savePendingAnswerStream,
} from "./sseResume";

const EPOCH = 1_800_000_000_000;

function makeEntry(overrides: Partial<{ sessionId: string; streamId: string; seq: number; startedAt: number }> = {}) {
  return {
    sessionId: overrides.sessionId ?? "sess-1",
    streamId: overrides.streamId ?? "stream-abc",
    seq: overrides.seq ?? 2,
    query: "Ngách tai nghe đang bật gì?",
    turnKind: "primary" as const,
    startedAt: overrides.startedAt ?? EPOCH,
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
    savePendingAnswerStream(makeEntry());
    const loaded = loadPendingAnswerStream("sess-1", EPOCH + 10_000);
    expect(loaded?.streamId).toBe("stream-abc");
    expect(loaded?.seq).toBe(2);
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

  it("TTL margin stays safely under Cloud Run's 120s replay buffer", () => {
    // Regression guard — the server-side buffer is 120s
    // (cloud-run/main.py). Leaving 30s slack absorbs clock drift +
    // trip-time so the auto-resume path does not miss the buffer.
    expect(PENDING_ANSWER_STREAM_MAX_AGE_MS).toBeLessThanOrEqual(120_000 - 30_000);
  });
});
