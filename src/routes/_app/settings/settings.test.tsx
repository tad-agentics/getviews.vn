/**
 * N-31 regression tests — settings flows.
 *
 * Covers:
 *   1. Logout dialog — open / cancel / confirm + navigate
 *   2. useUpdateProfile — optimistic update, onError rollback, cold-cache skip
 *   3. PlanPanel — free tier copy vs paid + expired copy
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { renderHook, act } from "@testing-library/react";

import { useLogout } from "@/hooks/useLogout";
import { supabase } from "@/lib/supabase";
import { useUpdateProfile } from "@/hooks/useUpdateProfile";
import * as profileData from "@/lib/data/profile";
import { queryKeys } from "@/lib/query-keys";
import type { ProfileRow } from "@/hooks/useProfile";
import { useProfile } from "@/hooks/useProfile";

// ── Shared mocks ─────────────────────────────────────────────────────────────

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: { signOut: vi.fn().mockResolvedValue({ error: null }) },
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: vi.fn(() => ({
    user: { id: "user-1", email: "test@getviews.vn" },
    session: { user: { id: "user-1" } },
    loading: false,
    signOut: vi.fn(),
  })),
}));

vi.mock("@/hooks/useProfile", () => ({
  useProfile: vi.fn(() => ({ data: null, isPending: false, isError: false, refetch: vi.fn() })),
}));

vi.mock("@/hooks/useSubscription", () => ({
  useSubscription: vi.fn(() => ({ data: null })),
}));

vi.mock("@/hooks/useCreditTransactions", () => ({
  useCreditTransactions: vi.fn(() => ({ data: [], isPending: false })),
}));

vi.mock("@/hooks/useNicheTaxonomy", () => ({
  useNicheTaxonomy: vi.fn(() => ({ data: [], isPending: false })),
}));

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// motion/react — render children without animation in tests
vi.mock("motion/react", () => {
  const React = require("react");
  const motion = new Proxy(
    {},
    {
      get: (_target, tag: string) =>
        // eslint-disable-next-line react/display-name
        React.forwardRef(
          (
            { children, ...props }: React.HTMLAttributes<HTMLElement>,
            ref: React.Ref<HTMLElement>,
          ) => React.createElement(tag, { ...props, ref }, children),
        ),
    },
  );
  return {
    motion,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

// ── Shared helpers ────────────────────────────────────────────────────────────

const MOCK_PROFILE: ProfileRow = {
  id: "user-1",
  display_name: "Nguyễn A",
  email: "test@getviews.vn",
  subscription_tier: "free",
  deep_credits_remaining: 10,
  primary_niche: null,
  credits_reset_at: null,
} as ProfileRow;

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function Wrapper({ children, qc }: { children: React.ReactNode; qc: QueryClient }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

async function importSettings() {
  const mod = await import("./SettingsScreen");
  return mod.default;
}

// ── 1. Logout dialog ─────────────────────────────────────────────────────────

describe("LogoutSection — dialog", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = makeQc();
    vi.mocked(supabase.auth.signOut).mockResolvedValue({ error: null } as never);
  });

  afterEach(() => cleanup());

  async function renderSettings() {
    const SettingsScreen = await importSettings();
    return render(
      <Wrapper qc={qc}>
        <SettingsScreen />
      </Wrapper>,
    );
  }

  it("opens the logout confirmation dialog on button click", async () => {
    await renderSettings();
    fireEvent.click(screen.getByRole("button", { name: /Đăng xuất/i }));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeTruthy();
      expect(screen.getByText("Đăng xuất khỏi GetViews?")).toBeTruthy();
    });
  });

  it("closes the dialog when Huỷ is clicked without logging out", async () => {
    await renderSettings();

    const triggerBtn = screen.getByRole("button", { name: /Đăng xuất/i, expanded: false });
    fireEvent.click(triggerBtn);
    await waitFor(() => screen.getByRole("dialog"));

    // fireEvent bypasses jsdom's pointer-events:none that Radix sets on the body
    fireEvent.click(screen.getByRole("button", { name: /Huỷ/i }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(supabase.auth.signOut).not.toHaveBeenCalled();
  });

  it("calls signOut and clears query cache on confirm", async () => {
    const clearSpy = vi.spyOn(qc, "clear");
    await renderSettings();

    const triggerBtn = screen.getByRole("button", { name: /Đăng xuất/i, expanded: false });
    fireEvent.click(triggerBtn);
    await waitFor(() => screen.getByRole("dialog"));

    const dialog = screen.getByRole("dialog");
    const buttons = dialog.querySelectorAll("button");
    // Last button in dialog is the confirm "Đăng xuất" button
    fireEvent.click(buttons[buttons.length - 1]);

    await waitFor(() => {
      expect(supabase.auth.signOut).toHaveBeenCalledOnce();
    });
    await waitFor(() => {
      expect(clearSpy).toHaveBeenCalled();
    });
  });
});

// ── 2. useUpdateProfile — optimistic update + onError rollback ────────────────

describe("useUpdateProfile", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = makeQc();
  });

  afterEach(() => cleanup());

  function renderUpdateProfile() {
    return renderHook(() => useUpdateProfile(), {
      wrapper: ({ children }) => <Wrapper qc={qc}>{children}</Wrapper>,
    });
  }

  it("applies optimistic update immediately before server responds", async () => {
    let resolveUpdate!: (v: ProfileRow) => void;
    vi.spyOn(profileData, "updateProfile").mockReturnValue(
      new Promise<ProfileRow>((res) => {
        resolveUpdate = res;
      }),
    );

    qc.setQueryData<ProfileRow>(queryKeys.profile("user-1"), MOCK_PROFILE);

    const { result } = renderUpdateProfile();
    act(() => {
      result.current.mutate({ display_name: "Nguyễn B" });
    });

    await waitFor(() => {
      const cached = qc.getQueryData<ProfileRow>(queryKeys.profile("user-1"));
      expect(cached?.display_name).toBe("Nguyễn B");
    });

    resolveUpdate({ ...MOCK_PROFILE, display_name: "Nguyễn B" });
  });

  it("rolls back optimistic update on server error", async () => {
    vi.spyOn(profileData, "updateProfile").mockRejectedValue(new Error("network error"));
    qc.setQueryData<ProfileRow>(queryKeys.profile("user-1"), MOCK_PROFILE);

    const { result } = renderUpdateProfile();
    act(() => {
      result.current.mutate({ display_name: "Nguyễn B" });
    });

    await waitFor(() => result.current.isError);

    const cached = qc.getQueryData<ProfileRow>(queryKeys.profile("user-1"));
    expect(cached?.display_name).toBe("Nguyễn A");
  });

  it("skips optimistic setQueryData when cache is cold (no previous data)", async () => {
    let resolveUpdate!: (v: ProfileRow) => void;
    vi.spyOn(profileData, "updateProfile").mockReturnValue(
      new Promise<ProfileRow>((res) => {
        resolveUpdate = res;
      }),
    );

    const { result } = renderUpdateProfile();
    act(() => {
      result.current.mutate({ display_name: "Nguyễn B" });
    });

    // Cold cache — no optimistic write because previous was undefined
    const cached = qc.getQueryData<ProfileRow>(queryKeys.profile("user-1"));
    expect(cached).toBeUndefined();

    resolveUpdate({ ...MOCK_PROFILE, display_name: "Nguyễn B" });
  });
});

// ── 3. PlanPanel — free vs paid copy ─────────────────────────────────────────

describe("PlanPanel — subscription copy", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = makeQc();
  });

  afterEach(() => cleanup());

  async function renderWithProfile(profileOverride: Partial<ProfileRow>) {
    vi.mocked(useProfile).mockReturnValue({
      data: { ...MOCK_PROFILE, ...profileOverride },
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    const SettingsScreen = await importSettings();
    return render(
      <Wrapper qc={qc}>
        <SettingsScreen />
      </Wrapper>,
    );
  }

  it("shows free-tier lifetime copy when user has no subscription", async () => {
    await renderWithProfile({ subscription_tier: "free" });
    await waitFor(() => {
      expect(screen.getAllByText(/10 lần phân tích sâu miễn phí/i).length).toBeGreaterThan(0);
    });
  });

  it("shows expired copy when paid subscription has passed credits_reset_at", async () => {
    const pastDate = new Date(Date.now() - 86400_000).toISOString();
    await renderWithProfile({ subscription_tier: "starter", credits_reset_at: pastDate });
    await waitFor(() => {
      expect(screen.getAllByText(/Gói đã hết hạn/i).length).toBeGreaterThan(0);
    });
  });

  it("shows credits expiry date for active paid subscription", async () => {
    const futureDate = new Date(Date.now() + 30 * 86400_000).toISOString();
    await renderWithProfile({ subscription_tier: "starter", credits_reset_at: futureDate });
    await waitFor(() => {
      expect(screen.getAllByText(/Credits hết hạn/i).length).toBeGreaterThan(0);
    });
  });
});
