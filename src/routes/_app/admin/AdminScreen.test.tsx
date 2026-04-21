/**
 * AdminScreen — routing + render gate regression.
 *
 * Two critical paths:
 *   1. Non-admin: navigate("/app", replace) fires after profile resolves.
 *      The admin shell must never render for a non-admin, even for a
 *      frame. (A misfire here would leak panel structure to anyone who
 *      types /app/admin directly. Server-side require_admin blocks the
 *      data fetches but the DOM should also stay clean.)
 *   2. Admin: panels mount inside the Studio chrome (TopBar + sections).
 *      We assert the kickers for all five sections so a panel
 *      accidentally dropped in a future refactor fails the test.
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

// ── Mocks ───────────────────────────────────────────────────────────
vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Stub every panel so the screen test stays focused on routing + section
// rhythm, not on downstream panel data fetching.
vi.mock("./CorpusHealthPanel", () => ({
  CorpusHealthPanel: () => <div data-testid="panel-corpus" />,
}));
vi.mock("./EnsembleCreditsPanel", () => ({
  EnsembleCreditsPanel: () => <div data-testid="panel-ensemble" />,
}));
vi.mock("./LogsPanel", () => ({
  LogsPanel: () => <div data-testid="panel-logs" />,
}));
vi.mock("./TriggersPanel", () => ({
  TriggersPanel: () => <div data-testid="panel-triggers" />,
}));
vi.mock("./ActionLogPanel", () => ({
  ActionLogPanel: () => <div data-testid="panel-actionlog" />,
}));
vi.mock("./AlertsPanel", () => ({
  AlertsPanel: () => <div data-testid="panel-alerts" />,
}));

// TopBar / SectionHeader — render enough structure to assert against.
vi.mock("@/components/v2/TopBar", () => ({
  TopBar: ({ kicker, title }: { kicker: string; title: string }) => (
    <header data-testid="topbar">
      <span data-testid="topbar-kicker">{kicker}</span>
      <h1 data-testid="topbar-title">{title}</h1>
    </header>
  ),
}));
vi.mock("@/components/v2/SectionHeader", () => ({
  SectionHeader: ({ kicker, title }: { kicker: string; title: string }) => (
    <header data-testid="section-header">
      <span data-testid={`kicker-${kicker}`}>{kicker}</span>
      <h2>{title}</h2>
    </header>
  ),
}));

const mockUseIsAdmin = vi.fn();
vi.mock("@/hooks/useIsAdmin", () => ({
  useIsAdmin: () => mockUseIsAdmin(),
}));

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const AdminScreen = (await import("./AdminScreen")).default;

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/app/admin"]}>
        <AdminScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockUseIsAdmin.mockReset();
  mockNavigate.mockReset();
});
afterEach(cleanup);

describe("AdminScreen gate", () => {
  it("shows a loading skeleton while the admin check is resolving", () => {
    mockUseIsAdmin.mockReturnValue({ isAdmin: false, isLoading: true });
    renderScreen();
    // Neither TopBar nor any panel should render during the loading state —
    // the shell renders a status skeleton instead.
    expect(screen.queryByTestId("topbar")).toBeNull();
    expect(screen.queryByTestId("panel-corpus")).toBeNull();
    expect(screen.getByRole("status", { name: /đang tải/i })).toBeTruthy();
  });

  it("redirects non-admins to /app and renders no admin chrome", async () => {
    mockUseIsAdmin.mockReturnValue({ isAdmin: false, isLoading: false });
    renderScreen();
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true });
    });
    // Nothing admin-shaped is in the DOM during the bounce.
    expect(screen.queryByTestId("topbar")).toBeNull();
    expect(screen.queryByTestId("panel-corpus")).toBeNull();
    expect(screen.queryByTestId("panel-triggers")).toBeNull();
  });

  it("renders the TopBar + all five sections when the user is admin", () => {
    mockUseIsAdmin.mockReturnValue({ isAdmin: true, isLoading: false });
    renderScreen();
    expect(mockNavigate).not.toHaveBeenCalled();

    expect(screen.getByTestId("topbar-title").textContent).toBe("Sức khỏe hệ thống");
    expect(screen.getByTestId("topbar-kicker").textContent).toContain("ADMIN");

    // Section kickers lock the rendering order / presence so a future
    // refactor that drops a section fails here rather than shipping a
    // half-empty dashboard.
    expect(screen.getByTestId("kicker-ALERTS · THRESHOLD RULES")).toBeTruthy();
    expect(screen.getByTestId("kicker-CORPUS · INGEST + CLAIM TIERS")).toBeTruthy();
    expect(screen.getByTestId("kicker-ENSEMBLEDATA · USED UNITS")).toBeTruthy();
    expect(screen.getByTestId("kicker-CLOUD RUN · STDOUT TAIL")).toBeTruthy();
    expect(screen.getByTestId("kicker-MANUAL RUN · CRON JOBS")).toBeTruthy();
    expect(screen.getByTestId("kicker-AUDIT · WHO RAN WHAT")).toBeTruthy();

    // All six panels mount.
    expect(screen.getByTestId("panel-alerts")).toBeTruthy();
    expect(screen.getByTestId("panel-corpus")).toBeTruthy();
    expect(screen.getByTestId("panel-ensemble")).toBeTruthy();
    expect(screen.getByTestId("panel-logs")).toBeTruthy();
    expect(screen.getByTestId("panel-triggers")).toBeTruthy();
    expect(screen.getByTestId("panel-actionlog")).toBeTruthy();
  });
});
