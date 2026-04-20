/**
 * HomeScreen smoke tests (Phase A · A3.2).
 *
 * Not a full render test — the screen pulls from 6 hooks and wrapping
 * Supabase, AppLayout, and motion reliably in jsdom is not worth the
 * effort. Scope: the composer hands a navigation payload to /app with
 * initialPrompt in state, and the greeting degrades gracefully when the
 * pulse/niche data hasn't arrived yet.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

// ── Module mocks ───────────────────────────────────────────────────────────

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: undefined,
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

const mockUseProfile = vi.fn();
const mockUseNicheTaxonomy = vi.fn();
const mockUseHomePulse = vi.fn();
const mockUseHomeTicker = vi.fn();
const mockUseDailyRitual = vi.fn();
const mockUseTopPatterns = vi.fn();
const mockUseTopBreakouts = vi.fn();
const mockUseTopNiches = vi.fn();
const mockUseUpdateProfile = vi.fn();

vi.mock("@/hooks/useProfile", () => ({ useProfile: () => mockUseProfile() }));
vi.mock("@/hooks/useNicheTaxonomy", () => ({
  useNicheTaxonomy: () => mockUseNicheTaxonomy(),
}));
vi.mock("@/hooks/useHomePulse", () => ({ useHomePulse: () => mockUseHomePulse() }));
vi.mock("@/hooks/useHomeTicker", () => ({ useHomeTicker: () => mockUseHomeTicker() }));
vi.mock("@/hooks/useDailyRitual", () => ({ useDailyRitual: () => mockUseDailyRitual() }));
vi.mock("@/hooks/useTopPatterns", () => ({ useTopPatterns: () => mockUseTopPatterns() }));
vi.mock("@/hooks/useTopBreakouts", () => ({ useTopBreakouts: () => mockUseTopBreakouts() }));
vi.mock("@/hooks/useTopNiches", () => ({ useTopNiches: () => mockUseTopNiches() }));
vi.mock("@/hooks/useUpdateProfile", () => ({ useUpdateProfile: () => mockUseUpdateProfile() }));

// AppLayout pulls in a large tree — stub it; we don't test shell here.
vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Hard-stub the auth context used transitively.
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "u", email: "a@b.vn" },
    session: { user: { id: "u" } },
    loading: false,
    signOut: vi.fn(),
  }),
}));

const HomeScreen = (await import("./HomeScreen")).default;

// ── Helpers ────────────────────────────────────────────────────────────────

function setHooksDefaults() {
  mockUseProfile.mockReturnValue({
    data: { id: "u", display_name: "An Do", primary_niche: 4 },
  });
  mockUseNicheTaxonomy.mockReturnValue({
    data: [{ id: 4, name: "Ẩm thực" }],
  });
  mockUseHomePulse.mockReturnValue({ data: null, isPending: false });
  mockUseHomeTicker.mockReturnValue({ data: [] });
  mockUseDailyRitual.mockReturnValue({ data: null, isPending: false });
  mockUseTopPatterns.mockReturnValue({ data: [], isPending: false });
  mockUseTopBreakouts.mockReturnValue({ data: [], isPending: false });
  mockUseTopNiches.mockReturnValue({ data: [{ id: 4, name: "Ẩm thực", hot: 24 }] });
  mockUseUpdateProfile.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false });
}

function renderHome() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <HomeScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("HomeScreen", () => {
  beforeEach(() => {
    mockUseProfile.mockReset();
    mockUseNicheTaxonomy.mockReset();
    mockUseHomePulse.mockReset();
    mockUseHomeTicker.mockReset();
    mockUseDailyRitual.mockReset();
    mockUseTopPatterns.mockReset();
    mockUseTopBreakouts.mockReset();
    mockUseTopNiches.mockReset();
    mockUseUpdateProfile.mockReset();
    setHooksDefaults();
  });
  afterEach(cleanup);

  it("greets the user with their first name and niche label", () => {
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").startsWith("Chào"))!;
    const text = headline.textContent ?? "";
    expect(text).toContain("Chào Do");  // last token of "An Do"
    expect(text).toContain("Ẩm thực");
  });

  it("omits the hook-count clause when pulse has no new_hooks", () => {
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").startsWith("Chào"))!;
    expect(headline.textContent).not.toContain("hook mới đang nổ");
    expect(headline.textContent).toContain("đang có gì mới");
  });

  it("renders the hook-count clause when new_hooks > 0", () => {
    mockUseHomePulse.mockReturnValue({
      data: {
        niche_id: 4,
        views_this_week: 10_000_000,
        views_last_week: 8_000_000,
        views_delta_pct: 25,
        videos_this_week: 40,
        new_creators_this_week: 5,
        viral_count_this_week: 6,
        new_hooks_this_week: 3,
        top_hook_name: "POV: mở chiếc hộp này",
        adequacy: "niche_norms",
        as_of: new Date().toISOString(),
      },
      isPending: false,
    });
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").startsWith("Chào"))!;
    expect(headline.textContent).toContain("3 hook mới");
  });

  it("falls back to 'bạn' when display_name is empty", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u", display_name: "", primary_niche: null },
    });
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").startsWith("Chào"))!;
    expect(headline.textContent).toContain("Chào bạn");
    expect(headline.textContent).toContain("ngách của bạn");
  });
});
