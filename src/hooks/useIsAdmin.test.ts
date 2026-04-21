/**
 * useIsAdmin — client-side admin gate regression.
 *
 * The hook is one line of logic but it's load-bearing: every entry
 * point to /app/admin (sidebar link + route guard) reads `isAdmin` to
 * decide whether to render. Three invariants the tests pin:
 *
 *   1. While the profile is loading, `isAdmin` is false (default-deny —
 *      the sidebar shouldn't flicker into admin visibility for a
 *      non-admin just because useProfile hasn't resolved yet).
 *   2. A profile with `is_admin: true` returns isAdmin=true.
 *   3. A profile with `is_admin: false` (or the column missing
 *      entirely, pre-migration) returns false.
 */
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
  },
}));

const mockUseProfile = vi.fn();
vi.mock("@/hooks/useProfile", () => ({
  useProfile: () => mockUseProfile(),
}));

import { useIsAdmin } from "./useIsAdmin";

describe("useIsAdmin", () => {
  it("returns isLoading=true while profile is loading, isAdmin=false (default-deny)", () => {
    mockUseProfile.mockReturnValue({ data: undefined, isLoading: true });
    const r = useIsAdmin();
    expect(r.isLoading).toBe(true);
    expect(r.isAdmin).toBe(false);
  });

  it("returns isAdmin=true when the profile carries is_admin=true", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u-1", is_admin: true },
      isLoading: false,
    });
    const r = useIsAdmin();
    expect(r.isLoading).toBe(false);
    expect(r.isAdmin).toBe(true);
  });

  it("returns isAdmin=false when is_admin is explicitly false", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u-1", is_admin: false },
      isLoading: false,
    });
    expect(useIsAdmin().isAdmin).toBe(false);
  });

  it("returns isAdmin=false when is_admin column is absent (pre-migration)", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u-1" },
      isLoading: false,
    });
    expect(useIsAdmin().isAdmin).toBe(false);
  });

  it("returns isAdmin=false when profile data is null (row doesn't exist)", () => {
    mockUseProfile.mockReturnValue({ data: null, isLoading: false });
    expect(useIsAdmin().isAdmin).toBe(false);
  });
});
