import { useCallback, useEffect, useState } from "react";
import type { ProfileRow } from "@/hooks/useProfile";

/**
 * Studio Home first-run detection (PR-6).
 *
 * The design's NGÀY ĐẦU TIÊN strip is meant to greet brand-new accounts
 * on their first session: niche-level data is hot from the corpus, but
 * the kênh's own comparison is still being built. We tag the user as
 * "first-run" when:
 *   • their ``profiles.created_at`` is within the last 24 hours, AND
 *   • they haven't dismissed the strip on this device.
 *
 * Dismissal is persisted in localStorage scoped to the user id so
 * multiple accounts on a shared device don't bleed into each other.
 */

const FIRST_RUN_WINDOW_MS = 24 * 60 * 60 * 1000;

function dismissalKey(userId: string): string {
  return `gv-firstrun-dismissed-${userId}`;
}

export function isProfileWithinFirstRunWindow(
  createdAtIso: string | null | undefined,
  now: Date = new Date(),
): boolean {
  if (!createdAtIso) return false;
  const created = new Date(createdAtIso);
  if (Number.isNaN(created.getTime())) return false;
  return now.getTime() - created.getTime() < FIRST_RUN_WINDOW_MS;
}

export function useIsFirstRun(profile: ProfileRow | null | undefined): {
  isFirstRun: boolean;
  dismiss: () => void;
} {
  const userId = profile?.id ?? null;
  const createdAt = profile?.created_at ?? null;

  // ``null`` while we wait for localStorage on mount; once known, true /
  // false controls visibility. Avoids a hydration flash where the strip
  // appears for a frame before localStorage check resolves.
  const [dismissed, setDismissed] = useState<boolean | null>(null);

  useEffect(() => {
    if (!userId) {
      setDismissed(null);
      return;
    }
    try {
      setDismissed(window.localStorage.getItem(dismissalKey(userId)) === "1");
    } catch {
      // SSR / private mode — fall back to "not dismissed" so the strip
      // can still render on day 1 in those edge cases.
      setDismissed(false);
    }
  }, [userId]);

  const dismiss = useCallback(() => {
    if (!userId) return;
    setDismissed(true);
    try {
      window.localStorage.setItem(dismissalKey(userId), "1");
    } catch {
      // Best-effort persistence; in-memory state still hides the strip.
    }
  }, [userId]);

  const inWindow = isProfileWithinFirstRunWindow(createdAt);
  const isFirstRun = inWindow && dismissed === false;

  return { isFirstRun, dismiss };
}
