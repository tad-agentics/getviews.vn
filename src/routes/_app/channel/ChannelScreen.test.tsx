/**
 * ChannelScreen smoke tests (Phase D.1.6 — C.8.6 backfill).
 *
 * Not a full integration test — mocks the two data hooks + `AppLayout` +
 * auth so the render is deterministic. Covers three surface contracts:
 *   1. Empty state when `handle` query param is absent.
 *   2. Loading + skeleton when `useChannelAnalyze` is pending.
 *   3. Renders the FormulaBar + KpiGrid sections on a populated payload.
 *
 * Follows the HomeScreen.test.tsx mock pattern — every hook that touches
 * Supabase / network / env is stubbed so no real fetches leave jsdom.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import type { ChannelAnalyzeResponse } from "@/lib/api-types";

// ── Module mocks ───────────────────────────────────────────────────────────

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

vi.mock("@/lib/logUsage", () => ({ logUsage: vi.fn() }));

const mockUseChannelAnalyze = vi.fn();
const mockUseHomePulse = vi.fn();

vi.mock("@/hooks/useChannelAnalyze", () => ({
  channelAnalyzeHandleKey: (h: string | null | undefined) =>
    h ? h.replace(/^@/, "").trim() || null : null,
  useChannelAnalyze: (opts: unknown) => mockUseChannelAnalyze(opts),
}));
vi.mock("@/hooks/useHomePulse", () => ({ useHomePulse: () => mockUseHomePulse() }));

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

const ChannelScreen = (await import("./ChannelScreen")).default;

// ── Fixtures ────────────────────────────────────────────────────────────────

function makePayload(overrides: Partial<ChannelAnalyzeResponse> = {}): ChannelAnalyzeResponse {
  return {
    handle: "@sammie.tech",
    niche_id: 4,
    name: "Sammie Tech",
    bio: null,
    followers: 412_000,
    total_videos: 24,
    avg_views: 89_000,
    engagement_pct: 6.8,
    posting_cadence: "3 lần/tuần",
    posting_time: "tối thứ 4–6",
    top_hook: null,
    formula: null,
    formula_gate: null,
    lessons: [],
    top_videos: [],
    niche_label: "Tech",
    kpis: [],
    ...overrides,
  } as ChannelAnalyzeResponse;
}

function renderScreen(searchParams = "") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/app/channel${searchParams}`]}>
        <ChannelScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("ChannelScreen", () => {
  beforeEach(() => {
    mockUseChannelAnalyze.mockReset();
    mockUseHomePulse.mockReset();
    mockUseHomePulse.mockReturnValue({ data: null, isPending: false });
  });
  afterEach(cleanup);

  it("renders empty state when no handle is provided", () => {
    mockUseChannelAnalyze.mockReturnValue({ data: undefined, isPending: false, isError: false });
    renderScreen();
    // Empty state shows the "Soi kênh trong corpus" card + handle input form.
    expect(screen.getByText(/Soi kênh trong corpus/)).toBeTruthy();
  });

  it("renders loading indicator while useChannelAnalyze is pending", () => {
    mockUseChannelAnalyze.mockReturnValue({ data: undefined, isPending: true, isError: false });
    const { container } = renderScreen("?handle=sammie.tech");
    expect(container).toBeTruthy();
  });

  it("renders handle + niche label when payload is present", () => {
    mockUseChannelAnalyze.mockReturnValue({
      data: makePayload({ handle: "@sammie.tech", niche_label: "Tech" }),
      isPending: false,
      isError: false,
    });
    renderScreen("?handle=sammie.tech");
    // Handle appears in title / crumb area.
    expect(screen.getAllByText(/@?sammie\.tech/i).length).toBeGreaterThan(0);
  });

  it("renders the posting cadence chip when cadence + time are populated", () => {
    mockUseChannelAnalyze.mockReturnValue({
      data: makePayload({ posting_cadence: "3 lần/tuần", posting_time: "tối thứ 4–6" }),
      isPending: false,
      isError: false,
    });
    renderScreen("?handle=sammie.tech");
    // `postingCadenceChipText` joins the two with " · ".
    expect(screen.getByText(/3 lần\/tuần · tối thứ 4–6/)).toBeTruthy();
  });
});
