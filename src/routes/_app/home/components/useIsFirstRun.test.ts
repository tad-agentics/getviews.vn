/**
 * PR-6 Studio Home — useIsFirstRun + isProfileWithinFirstRunWindow.
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { ProfileRow } from "@/hooks/useProfile";
import { isProfileWithinFirstRunWindow, useIsFirstRun } from "./useIsFirstRun";

beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  window.localStorage.clear();
});

function makeProfile(overrides: Partial<ProfileRow> = {}): ProfileRow {
  return {
    id: "u1",
    created_at: new Date().toISOString(),
    avatar_url: null,
    credits_reset_at: null,
    daily_free_query_count: 0,
    daily_free_query_reset_at: null,
    deep_credits_remaining: 0,
    display_name: "An",
    email: "a@b.vn",
    is_admin: false,
    is_processing: false,
    lifetime_credits_used: 0,
    primary_niche: 4,
    niche_ids: [4],
    reference_channel_handles: [],
    subscription_tier: "free",
    tiktok_handle: null,
    updated_at: new Date().toISOString(),
    ...overrides,
  } as ProfileRow;
}

describe("isProfileWithinFirstRunWindow", () => {
  const NOW = new Date("2026-04-26T12:00:00Z");

  it("returns true for accounts created within the last 24h", () => {
    const created = new Date("2026-04-25T15:00:00Z").toISOString();
    expect(isProfileWithinFirstRunWindow(created, NOW)).toBe(true);
  });

  it("returns false for accounts older than 24h", () => {
    const created = new Date("2026-04-24T11:00:00Z").toISOString();
    expect(isProfileWithinFirstRunWindow(created, NOW)).toBe(false);
  });

  it("returns false for null / undefined / unparseable inputs", () => {
    expect(isProfileWithinFirstRunWindow(null, NOW)).toBe(false);
    expect(isProfileWithinFirstRunWindow(undefined, NOW)).toBe(false);
    expect(isProfileWithinFirstRunWindow("not-a-date", NOW)).toBe(false);
  });
});

describe("useIsFirstRun", () => {
  it("returns isFirstRun=true when profile is fresh and not dismissed", () => {
    const profile = makeProfile({ created_at: new Date().toISOString() });
    const { result } = renderHook(() => useIsFirstRun(profile));
    expect(result.current.isFirstRun).toBe(true);
  });

  it("returns isFirstRun=false when profile is older than 24h", () => {
    const created = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString();
    const profile = makeProfile({ created_at: created });
    const { result } = renderHook(() => useIsFirstRun(profile));
    expect(result.current.isFirstRun).toBe(false);
  });

  it("returns isFirstRun=false when localStorage already has the dismissal flag", () => {
    window.localStorage.setItem("gv-firstrun-dismissed-u1", "1");
    const profile = makeProfile({ created_at: new Date().toISOString() });
    const { result } = renderHook(() => useIsFirstRun(profile));
    expect(result.current.isFirstRun).toBe(false);
  });

  it("dismiss() persists per-user and flips isFirstRun to false", () => {
    const profile = makeProfile({ created_at: new Date().toISOString() });
    const { result } = renderHook(() => useIsFirstRun(profile));
    expect(result.current.isFirstRun).toBe(true);
    act(() => {
      result.current.dismiss();
    });
    expect(result.current.isFirstRun).toBe(false);
    expect(window.localStorage.getItem("gv-firstrun-dismissed-u1")).toBe("1");
  });

  it("returns false while undefined profile is still loading", () => {
    const { result } = renderHook(() => useIsFirstRun(undefined));
    expect(result.current.isFirstRun).toBe(false);
  });
});
