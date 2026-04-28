/**
 * HomeScreen smoke tests (Phase A · A3.2).
 *
 * Not a full render test — the screen pulls from 6 hooks and wrapping
 * Supabase, AppLayout, and motion reliably in jsdom is not worth the
 * effort. Scope: the composer hands a navigation payload to /app with
 * initialPrompt in state, and the greeting degrades gracefully when the
 * niche data hasn't arrived yet.
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
const mockUseHomeTicker = vi.fn();
const mockUseDailyRitual = vi.fn();
const mockUseTopPatterns = vi.fn();
const mockUseTopBreakouts = vi.fn();
const mockUseTopNiches = vi.fn();
const mockUseNicheRowsForIds = vi.fn();
const mockUseUpdateProfile = vi.fn();

vi.mock("@/hooks/useProfile", () => ({ useProfile: () => mockUseProfile() }));
vi.mock("@/hooks/useNicheTaxonomy", () => ({
  useNicheTaxonomy: () => mockUseNicheTaxonomy(),
}));
vi.mock("@/hooks/useHomeTicker", () => ({ useHomeTicker: () => mockUseHomeTicker() }));
vi.mock("@/hooks/useDailyRitual", () => ({ useDailyRitual: () => mockUseDailyRitual() }));
vi.mock("@/hooks/useTopPatterns", () => ({
  useTopPatterns: () => mockUseTopPatterns(),
  // ``HooksTable`` (rendered via HomeScreen) imports this constant
  // alongside ``useTopPatterns`` to set its row limit. The mock factory
  // must export it too — vi.mock replaces the whole module, so an
  // omitted export becomes undefined and the component crashes
  // ("No 'STUDIO_HOME_TOP_PATTERNS_LIMIT' export is defined…").
  STUDIO_HOME_TOP_PATTERNS_LIMIT: 6,
}));
vi.mock("@/hooks/useTopBreakouts", () => ({ useTopBreakouts: () => mockUseTopBreakouts() }));
vi.mock("@/hooks/useTopNiches", () => ({
  useTopNiches: () => mockUseTopNiches(),
  useNicheRowsForIds: (...args: unknown[]) => mockUseNicheRowsForIds(...args),
}));
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
  mockUseHomeTicker.mockReturnValue({ data: [] });
  mockUseDailyRitual.mockReturnValue({
    data: null,
    emptyReason: null,
    isPending: false,
    refetch: vi.fn(),
  });
  mockUseTopPatterns.mockReturnValue({ data: [], isPending: false });
  mockUseTopBreakouts.mockReturnValue({ data: [], isPending: false });
  mockUseTopNiches.mockReturnValue({ data: [{ id: 4, name: "Ẩm thực", hot: 24 }] });
  mockUseNicheRowsForIds.mockReturnValue({ data: [] });
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
    mockUseHomeTicker.mockReset();
    mockUseDailyRitual.mockReset();
    mockUseTopPatterns.mockReset();
    mockUseTopBreakouts.mockReset();
    mockUseTopNiches.mockReset();
    mockUseNicheRowsForIds.mockReset();
    mockUseUpdateProfile.mockReset();
    setHooksDefaults();
  });
  afterEach(cleanup);

  it("greets the user with 'Chào {firstName}. Hôm nay' + niche label", () => {
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").includes("Hôm nay"))!;
    const text = headline.textContent ?? "";
    expect(text).toContain("Chào Do. Hôm nay");  // last token of "An Do"
    expect(text).toContain("Ẩm thực");
  });

  it("falls back to 'đang có gì mới' when no hot-new hooks are present", () => {
    // Default mock: useTopPatterns returns []; no patterns where prev=0.
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").includes("Hôm nay"))!;
    expect(headline.textContent).not.toContain("hook mới");
    expect(headline.textContent).toContain("đang có gì mới");
  });

  it("renders 'có N hook mới đang nổ' when patterns include some with prev=0", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [
        // Two truly-new (prev=0), one growing-from-existing.
        {
          id: "p1",
          display_name: "Hook mới 1",
          weekly_instance_count: 12,
          weekly_instance_count_prev: 0,
          instance_count: 12,
          niche_spread: [4],
          avg_views: 0,
          sample_hook: null,
        },
        {
          id: "p2",
          display_name: "Hook mới 2",
          weekly_instance_count: 8,
          weekly_instance_count_prev: 0,
          instance_count: 8,
          niche_spread: [4],
          avg_views: 0,
          sample_hook: null,
        },
        {
          id: "p3",
          display_name: "Hook đang lên",
          weekly_instance_count: 16,
          weekly_instance_count_prev: 4,
          instance_count: 28,
          niche_spread: [4],
          avg_views: 0,
          sample_hook: null,
        },
      ],
      isPending: false,
    });
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").includes("Hôm nay"))!;
    expect(headline.textContent).toContain("2 hook");
    expect(headline.textContent).toContain("mới đang nổ");
    expect(headline.textContent).not.toContain("đang có gì mới");
  });

  it("falls back to 'Bạn' when display_name is empty", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u", display_name: "", primary_niche: null },
    });
    renderHome();
    const headline = screen
      .getAllByRole("heading", { level: 1 })
      .find((el) => (el.textContent ?? "").includes("Hôm nay"))!;
    expect(headline.textContent).toContain("Chào Bạn. Hôm nay");
    expect(headline.textContent).toContain("ngách của bạn");
  });

  it("renders the corpus count chip when the selected niche has hot > 0", () => {
    // Default mock: useNicheRowsForIds returns []. Override to surface a
    // niche with a hot count matching the user's selected niche.
    mockUseProfile.mockReturnValue({
      data: { id: "u", display_name: "An", primary_niche: 4, niche_ids: [4] },
    });
    mockUseNicheRowsForIds.mockReturnValue({
      data: [{ id: 4, name: "Ẩm thực", hot: 1240 }],
    });
    renderHome();
    expect(screen.getByText(/1,240\+ video/)).toBeTruthy();
  });

  it("hides the corpus count chip when the selected niche has hot = 0", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u", display_name: "An", primary_niche: 4, niche_ids: [4] },
    });
    mockUseNicheRowsForIds.mockReturnValue({
      data: [{ id: 4, name: "Ẩm thực", hot: 0 }],
    });
    renderHome();
    expect(screen.queryByText(/\+ video/)).toBeNull();
  });
});
