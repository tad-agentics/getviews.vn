/**
 * `injectOptimisticTurn` — regression for the replication-lag race.
 *
 * When the SSE stream for `/answer` completes, the server row exists but
 * `GET /answer/sessions/:id` may still race a stale read replica and return
 * an empty `turns` array. The helper writes the just-streamed turn into the
 * React Query cache so the UI renders immediately, with `turn_index` dedup
 * so the real server row replaces the synthesized one on the next refetch.
 */
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: undefined,
  },
}));

vi.mock("@/lib/supabase", () => ({
  supabase: { auth: { getSession: vi.fn() } },
}));

import {
  injectOptimisticTurn,
  lastPayloadFromTurns,
  type AnswerDetailCache,
} from "./useAnswerSessionQueries";
import type { AnswerTurnRow, ReportV1 } from "@/lib/api-types";

function mkPayload(tag: string): ReportV1 {
  return {
    kind: "generic",
    report: {
      summary: tag,
      sources: [],
      related_questions: [],
    },
  } as unknown as ReportV1;
}

function mkTurn(index: number, tag = `t${index}`): AnswerTurnRow {
  return {
    id: `turn-${tag}`,
    session_id: "sess-1",
    turn_index: index,
    kind: index === 0 ? "primary" : "generic",
    query: `q-${tag}`,
    payload: mkPayload(tag),
  };
}

const BASE_SESSION = {
  id: "sess-1",
  user_id: "user-1",
  title: null,
  initial_q: "hỏi gì đó",
  intent_type: "follow_up_unclassifiable",
  format: "generic" as const,
  niche_id: null,
};

describe("injectOptimisticTurn", () => {
  it("seeds a fresh cache with the fallback session when none exists", () => {
    const turn = mkTurn(0);
    const next = injectOptimisticTurn(undefined, BASE_SESSION, turn);
    expect(next.session).toEqual(BASE_SESSION);
    expect(next.turns).toEqual([turn]);
  });

  it("appends when turn_index is new", () => {
    const current: AnswerDetailCache = {
      session: BASE_SESSION,
      turns: [mkTurn(0)],
    };
    const follow = mkTurn(1, "follow");
    const next = injectOptimisticTurn(current, BASE_SESSION, follow);
    expect(next.turns).toHaveLength(2);
    expect(next.turns[1]).toBe(follow);
  });

  it("replaces in place when turn_index already exists (dedup server row over optimistic)", () => {
    const optimistic = { ...mkTurn(0), id: "optimistic-sess-1-0" };
    const current: AnswerDetailCache = {
      session: BASE_SESSION,
      turns: [optimistic],
    };
    const authoritative = mkTurn(0, "real");
    const next = injectOptimisticTurn(current, BASE_SESSION, authoritative);
    expect(next.turns).toHaveLength(1);
    expect(next.turns[0]).toBe(authoritative);
  });

  it("preserves existing session metadata (does not overwrite with fallback)", () => {
    const realSession = { ...BASE_SESSION, title: "Đã có tiêu đề thật" };
    const current: AnswerDetailCache = { session: realSession, turns: [] };
    const next = injectOptimisticTurn(current, BASE_SESSION, mkTurn(0));
    expect(next.session.title).toBe("Đã có tiêu đề thật");
  });
});

describe("lastPayloadFromTurns", () => {
  it("returns null when turns are undefined or empty", () => {
    expect(lastPayloadFromTurns(undefined)).toBeNull();
    expect(lastPayloadFromTurns([])).toBeNull();
  });

  it("returns the payload of the last turn", () => {
    const turns = [mkTurn(0), mkTurn(1, "latest")];
    const last = lastPayloadFromTurns(turns);
    expect(last).toBe(turns[1].payload);
  });
});
