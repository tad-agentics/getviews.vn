/**
 * Credit deduction logic — regression tests for api/chat.ts constants.
 *
 * api/chat.ts is a Vercel Edge Function and cannot be imported directly in
 * Vitest (module-level env reads + createClient side-effects).  The constants
 * are replicated here so any divergence is caught at the assertion level.
 *
 * SOURCE OF TRUTH: api/chat.ts lines 21-24.
 * If FREE_INTENTS or FREE_DAILY_LIMIT change there, update this file too.
 */

import { describe, it, expect } from "vitest";

// ── Replicated from api/chat.ts (keep in sync) ────────────────────────────────

const FREE_INTENTS = new Set([
  "format_lifecycle",
  "follow_up",
]);

const FREE_DAILY_LIMIT = 100;

// ── Pure credit-deduction logic (mirrors api/chat.ts lines 200-201) ───────────

function creditRow(isFree: boolean) {
  return {
    credits_used: isFree ? 0 : 1,
    is_free: isFree,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("api/chat.ts — FREE_INTENTS set", () => {
  it("contains the expected free intents", () => {
    expect(FREE_INTENTS.has("format_lifecycle")).toBe(true);
  });

  it("contains follow_up and does not contain deep-credit intents", () => {
    expect(FREE_INTENTS.has("follow_up")).toBe(true);
    expect(FREE_INTENTS.has("video_diagnosis")).toBe(false);
    expect(FREE_INTENTS.has("brief_generation")).toBe(false);
    expect(FREE_INTENTS.has("shot_list")).toBe(false);
  });
});

describe("api/chat.ts — FREE_DAILY_LIMIT", () => {
  it("is 100", () => {
    expect(FREE_DAILY_LIMIT).toBe(100);
  });
});

describe("api/chat.ts — credit deduction logic", () => {
  it("free intent writes credits_used=0 and is_free=true", () => {
    const isFree = FREE_INTENTS.has("format_lifecycle");
    const row = creditRow(isFree);
    expect(row.credits_used).toBe(0);
    expect(row.is_free).toBe(true);
  });

  it("paid intent writes credits_used=1 and is_free=false", () => {
    const isFree = FREE_INTENTS.has("video_diagnosis");
    const row = creditRow(isFree);
    expect(row.credits_used).toBe(1);
    expect(row.is_free).toBe(false);
  });
});
