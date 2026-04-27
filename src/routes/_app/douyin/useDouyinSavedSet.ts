import { useCallback, useEffect, useState } from "react";

/**
 * D4b (2026-06-04) — localStorage-backed saved set for Kho Douyin.
 *
 * Per the design pack ``screens/douyin.jsx`` lines 476-492: every video
 * card has a save toggle (top-right of thumbnail), and the toolbar's
 * "Kho cá nhân" filter narrows the grid to saved-only. Persists in
 * localStorage under ``gv-douyin-saved`` so the set survives page
 * reloads.
 *
 * Cloud-sync to user_profiles is an explicit follow-up (D4 ships
 * localStorage-only — no migration / RLS work). When that lands, the
 * hook's hot path stays the same; only the persistence layer swaps.
 *
 * SSR-safe — the initial state is a fresh empty Set during prerender;
 * the localStorage hydration runs in the post-mount effect (mirrors
 * the pattern in ``src/routes/_app/home/components/useIsFirstRun.ts``).
 */

const STORAGE_KEY = "gv-douyin-saved";

function _readFromStorage(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(
      parsed.filter((v): v is string => typeof v === "string" && v.length > 0),
    );
  } catch {
    return new Set();
  }
}

function _writeToStorage(set: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([...set].slice(0, 500)),
    );
  } catch {
    /* QuotaExceeded — silent. The set lives in-memory regardless. */
  }
}

export function useDouyinSavedSet() {
  // SSR-safe: start empty on prerender, hydrate post-mount.
  const [set, setSet] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setSet(_readFromStorage());
    // Listen to the ``storage`` event so toggling in one tab updates
    // any others open on the same surface.
    const onStorage = (e: StorageEvent): void => {
      if (e.key === STORAGE_KEY) {
        setSet(_readFromStorage());
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const toggle = useCallback((videoId: string): void => {
    if (!videoId) return;
    setSet((prev) => {
      const next = new Set(prev);
      if (next.has(videoId)) {
        next.delete(videoId);
      } else {
        next.add(videoId);
      }
      _writeToStorage(next);
      return next;
    });
  }, []);

  const has = useCallback(
    (videoId: string | null | undefined): boolean => {
      if (!videoId) return false;
      return set.has(videoId);
    },
    [set],
  );

  return { set, toggle, has, size: set.size };
}
