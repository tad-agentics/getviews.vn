/**
 * ScriptScreen smoke tests (Phase D.1.6 — C.8.6 backfill).
 *
 * Same mock philosophy as ChannelScreen.test.tsx: every hook that
 * touches Supabase / network / env is stubbed so the render is
 * deterministic. Covers three branch contracts:
 *   1. Env-gate: renders the missing VITE_CLOUD_RUN_API_URL message.
 *   2. Niche-gate: renders the "Chọn ngách" prompt when no niche is
 *      resolvable.
 *   3. Happy path: renders topic heading + script-number kicker.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

// ── Module mocks ───────────────────────────────────────────────────────────

const mockEnv = {
  VITE_SUPABASE_URL: "https://test.supabase.co",
  VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
  VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
  VITE_R2_PUBLIC_URL: undefined as string | undefined,
};

vi.mock("@/lib/env", () => ({ env: mockEnv }));
vi.mock("@/lib/logUsage", () => ({ logUsage: vi.fn() }));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    from: () => ({
      select: () => ({
        in: () => Promise.resolve({ data: [], error: null }),
      }),
    }),
  },
}));

const mockUseProfile = vi.fn();
const mockUseHomePulse = vi.fn();
const mockUseScriptSceneIntelligence = vi.fn();
const mockUseScriptHookPatterns = vi.fn();
const mockUseScriptGenerate = vi.fn();

vi.mock("@/hooks/useProfile", () => ({ useProfile: () => mockUseProfile() }));
vi.mock("@/hooks/useHomePulse", () => ({ useHomePulse: () => mockUseHomePulse() }));
vi.mock("@/hooks/useScriptSceneIntelligence", () => ({
  useScriptSceneIntelligence: (id: number | null) => mockUseScriptSceneIntelligence(id),
}));
vi.mock("@/hooks/useScriptHookPatterns", () => ({
  useScriptHookPatterns: (id: number | null) => mockUseScriptHookPatterns(id),
}));
vi.mock("@/hooks/useScriptGenerate", () => ({
  useScriptGenerate: () => mockUseScriptGenerate(),
}));

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "u", email: "a@b.vn" },
    session: { user: { id: "u" } },
    loading: false,
    signOut: vi.fn(),
  }),
}));

const ScriptScreen = (await import("./ScriptScreen")).default;

// ── Helpers ────────────────────────────────────────────────────────────────

function renderScreen(searchParams = "") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/app/script${searchParams}`]}>
        <ScriptScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("ScriptScreen", () => {
  beforeEach(() => {
    mockEnv.VITE_CLOUD_RUN_API_URL = "https://cloud-run.test";
    mockUseProfile.mockReset();
    mockUseHomePulse.mockReset();
    mockUseScriptSceneIntelligence.mockReset();
    mockUseScriptHookPatterns.mockReset();
    mockUseScriptGenerate.mockReset();

    mockUseProfile.mockReturnValue({ data: { primary_niche: 4 } });
    mockUseHomePulse.mockReturnValue({ data: null, isPending: false });
    mockUseScriptSceneIntelligence.mockReturnValue({ data: null, isPending: false });
    mockUseScriptHookPatterns.mockReturnValue({ data: null, isPending: false });
    mockUseScriptGenerate.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
    });
  });
  afterEach(cleanup);

  it("renders the env-gate message when VITE_CLOUD_RUN_API_URL is missing", () => {
    mockEnv.VITE_CLOUD_RUN_API_URL = "" as unknown as string;
    renderScreen();
    expect(screen.getByText(/VITE_CLOUD_RUN_API_URL/)).toBeTruthy();
  });

  it("renders the niche-gate prompt when profile has no niche and no ?niche_id query", () => {
    mockUseProfile.mockReturnValue({ data: { primary_niche: null } });
    renderScreen();
    expect(screen.getByText(/Chọn ngách trong onboarding/)).toBeTruthy();
  });

  it("renders the loading banner while scene or hook queries are pending", () => {
    mockUseScriptSceneIntelligence.mockReturnValue({ data: null, isPending: true });
    mockUseScriptHookPatterns.mockReturnValue({ data: null, isPending: false });
    renderScreen();
    expect(screen.getByText(/Đang tải dữ liệu ngách/)).toBeTruthy();
  });

  it("renders the topic heading + KỊCH BẢN SỐ kicker on the happy path", () => {
    renderScreen();
    // Default topic seeded inside ScriptScreen — "Review tai nghe 200k vs 2 triệu".
    // Text appears in both the <h1> and the <textarea> value, so scope to the heading.
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toMatch(/Review tai nghe 200k vs 2 triệu/);
    expect(screen.getByText(/XƯỞNG VIẾT · KỊCH BẢN SỐ/)).toBeTruthy();
  });

  it("honours ?topic= to pre-fill the heading", () => {
    renderScreen("?topic=" + encodeURIComponent("Test topic từ query"));
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toMatch(/Test topic từ query/);
  });
});
