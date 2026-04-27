/**
 * D4b (2026-06-04) — useDouyinSavedSet tests.
 *
 * Tests the localStorage-backed saved-set hook used by the Kho Douyin
 * video card save toggle. SSR safety + persistence + multi-tab sync.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useDouyinSavedSet } from "./useDouyinSavedSet";

const STORAGE_KEY = "gv-douyin-saved";


beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});


describe("useDouyinSavedSet", () => {
  it("starts with an empty set when localStorage is empty", () => {
    const { result } = renderHook(() => useDouyinSavedSet());
    expect(result.current.size).toBe(0);
    expect(result.current.has("v1")).toBe(false);
  });

  it("hydrates from localStorage on mount", () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(["v1", "v2"]));
    const { result } = renderHook(() => useDouyinSavedSet());
    // useEffect runs after render — wait a tick.
    expect(result.current.size).toBe(2);
    expect(result.current.has("v1")).toBe(true);
    expect(result.current.has("v2")).toBe(true);
  });

  it("toggle() adds a video_id and persists to localStorage", () => {
    const { result } = renderHook(() => useDouyinSavedSet());
    act(() => result.current.toggle("v1"));
    expect(result.current.has("v1")).toBe(true);
    expect(result.current.size).toBe(1);
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
    expect(stored).toContain("v1");
  });

  it("toggle() on an existing video_id removes it", () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(["v1"]));
    const { result } = renderHook(() => useDouyinSavedSet());
    expect(result.current.has("v1")).toBe(true);
    act(() => result.current.toggle("v1"));
    expect(result.current.has("v1")).toBe(false);
    expect(result.current.size).toBe(0);
  });

  it("toggle() with empty string is a no-op", () => {
    const { result } = renderHook(() => useDouyinSavedSet());
    act(() => result.current.toggle(""));
    expect(result.current.size).toBe(0);
  });

  it("has() with null/undefined returns false", () => {
    const { result } = renderHook(() => useDouyinSavedSet());
    expect(result.current.has(null)).toBe(false);
    expect(result.current.has(undefined)).toBe(false);
  });

  it("ignores malformed localStorage payload (not a JSON array)", () => {
    window.localStorage.setItem(STORAGE_KEY, "not-json");
    const { result } = renderHook(() => useDouyinSavedSet());
    expect(result.current.size).toBe(0);
  });

  it("ignores non-string entries when hydrating", () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(["v1", 42, null, "", "v2"]),
    );
    const { result } = renderHook(() => useDouyinSavedSet());
    expect(result.current.size).toBe(2);
    expect(result.current.has("v1")).toBe(true);
    expect(result.current.has("v2")).toBe(true);
  });

  it("syncs across instances via the storage event", () => {
    const { result } = renderHook(() => useDouyinSavedSet());
    expect(result.current.size).toBe(0);

    // Simulate another tab adding a value + emitting a storage event.
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(["v_other_tab"]));
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: STORAGE_KEY,
          newValue: JSON.stringify(["v_other_tab"]),
        }),
      );
    });
    expect(result.current.has("v_other_tab")).toBe(true);
  });
});
