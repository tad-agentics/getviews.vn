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
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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

vi.mock("@/hooks/useNicheTaxonomy", () => ({
  useNicheTaxonomy: () => ({ data: [{ id: 4, name: "Làm đẹp" }] }),
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

// Default to a ``?topic=`` param so the test mounts ScriptDetailScreen,
// not the new IdeaWorkspace step-1 surface. Workspace behavior is covered
// by IdeaWorkspace.test.tsx.
function renderScreen(searchParams = "?topic=Review+tai+nghe+200k+vs+2+tri%E1%BB%87u") {
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
    mockUseScriptSceneIntelligence.mockReturnValue({
      data: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseScriptHookPatterns.mockReturnValue({
      data: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
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
    mockUseScriptSceneIntelligence.mockReturnValue({
      data: null,
      isPending: true,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseScriptHookPatterns.mockReturnValue({
      data: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen();
    expect(screen.getByText(/Đang tải dữ liệu ngách/)).toBeTruthy();
  });

  it("shows niche data error banner with retry when hook-patterns query errors", () => {
    const hookRefetch = vi.fn();
    const sceneRefetch = vi.fn();
    mockUseScriptHookPatterns.mockReturnValue({
      data: null,
      isPending: false,
      isError: true,
      refetch: hookRefetch,
    });
    mockUseScriptSceneIntelligence.mockReturnValue({
      data: null,
      isPending: false,
      isError: false,
      refetch: sceneRefetch,
    });
    renderScreen();
    expect(screen.getByText(/Không tải được dữ liệu ngách/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Thử lại/i }));
    expect(hookRefetch).toHaveBeenCalledTimes(1);
    expect(sceneRefetch).toHaveBeenCalledTimes(1);
  });

  it("hook-timing helper mentions generic window and not hardcoded Tech", () => {
    renderScreen();
    expect(screen.getByText(/Hầu hết video thắng rơi hook/)).toBeTruthy();
    expect(screen.getByText(/0\.8.*1\.4s/)).toBeTruthy();
    expect(screen.queryByText(/ngách Tech/i)).toBeNull();
  });

  it("renders the topic textarea + KỊCH BẢN SỐ kicker on the happy path", () => {
    renderScreen();
    // S6 — header H1 became an editable textarea (per design pack
    // ``screens/script.jsx`` lines 663-686). Two textareas now share the
    // ``topic`` state — the header (aria-label "Chủ đề kịch bản") and
    // the sidebar CHỦ ĐỀ field. We assert against the header one.
    const headerTopic = screen.getByLabelText(/Chủ đề kịch bản/) as HTMLTextAreaElement;
    expect(headerTopic.value).toMatch(/Review tai nghe 200k vs 2 triệu/);
    expect(screen.getByText(/XƯỞNG VIẾT · KỊCH BẢN SỐ/)).toBeTruthy();
  });

  it("honours ?topic= to pre-fill the topic textarea", () => {
    renderScreen("?topic=" + encodeURIComponent("Test topic từ query"));
    const headerTopic = screen.getByLabelText(/Chủ đề kịch bản/) as HTMLTextAreaElement;
    expect(headerTopic.value).toMatch(/Test topic từ query/);
  });
});
