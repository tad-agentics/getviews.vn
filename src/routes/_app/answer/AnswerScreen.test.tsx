/**
 * AnswerScreen — integration coverage for the three states that previously
 * conflated "no report produced" with "report produced but not visible":
 *
 *   1. No session + no seed query → the "dán câu hỏi" empty-state prompt.
 *   2. Session exists + detail returns turns → each turn renders via the
 *      ContinuationTurn dispatcher (PatternBody et al. are stubbed — we
 *      only assert the turn-row reaches the dispatcher).
 *   3. Session exists + detail returns an empty `turns` array → the
 *      "Chưa có lượt" diagnostic card + functional "Tải lại phiên" button
 *      that calls `detailQuery.refetch()`.
 *
 * Everything below AnswerShell is passthrough-mocked to avoid dragging in
 * the full primitive tree (which has its own Supabase-shaped fixtures).
 * The behavioral invariant is the state transitions above — not the visual
 * pixels, which the Studio UIUX reference owns.
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import type { AnswerSessionRow, AnswerTurnRow, ReportV1 } from "@/lib/api-types";

// ── Module mocks ───────────────────────────────────────────────────────────
vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: "test-token" } },
      }),
    },
  },
}));

vi.mock("@/lib/logUsage", () => ({ logUsage: vi.fn() }));

vi.mock("@/lib/answerApi", () => ({
  createAnswerSession: vi.fn(),
  fetchAnswerSessions: vi.fn().mockResolvedValue({ sessions: [], next_cursor: null }),
  fetchAnswerSessionDetail: vi.fn(),
}));

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Stub the visual shell primitives — behavioral tests don't care which div
// wraps what, only that the slot contents are reachable in the DOM.
vi.mock("@/components/v2/answer/AnswerShell", () => ({
  AnswerShell: ({
    crumb,
    header,
    main,
    aside,
  }: {
    crumb?: React.ReactNode;
    header?: React.ReactNode;
    main?: React.ReactNode;
    aside?: React.ReactNode;
  }) => (
    <div data-testid="answer-shell">
      <div data-testid="crumb">{crumb}</div>
      <div data-testid="header">{header}</div>
      <div data-testid="main">{main}</div>
      <div data-testid="aside">{aside}</div>
    </div>
  ),
}));
vi.mock("@/components/v2/answer/QueryHeader", () => ({
  QueryHeader: ({ title, children }: { title?: string; children?: React.ReactNode }) => (
    <div data-testid="query-header">
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));
vi.mock("@/components/v2/answer/SessionDrawer", () => ({
  SessionDrawer: () => <div data-testid="session-drawer" />,
}));
vi.mock("@/components/v2/answer/FollowUpComposer", () => ({
  FollowUpComposer: ({
    disabled,
  }: {
    disabled?: boolean;
    value: string;
    onChange: (v: string) => void;
    onSubmit: () => void;
  }) => (
    <div data-testid="follow-up-composer" data-disabled={String(disabled ?? false)} />
  ),
}));
vi.mock("@/components/v2/answer/AnswerSourcesCard", () => ({
  AnswerSourcesCard: () => <div data-testid="sources-card" />,
}));
vi.mock("@/components/v2/answer/TemplatizeCard", () => ({
  TemplatizeCard: () => <div data-testid="templatize-card" />,
}));
vi.mock("@/components/v2/answer/ResearchStrip", () => ({
  MiniResearchStrip: () => null,
  ProgressPill: () => null,
  ResearchStepStrip: () => null,
  useResearchStage: () => 0,
}));
vi.mock("@/components/v2/answer/RelatedQs", () => ({
  RelatedQs: () => <div data-testid="related-qs" />,
}));
vi.mock("@/components/v2/answer/TimelineRail", () => ({
  TimelineRail: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="timeline-rail">{children}</div>
  ),
}));
vi.mock("@/components/v2/answer/ContinuationTurn", () => ({
  ContinuationTurn: ({ turn }: { turn: AnswerTurnRow }) => (
    <div data-testid={`turn-${turn.turn_index}`}>
      <span data-testid={`turn-kind-${turn.turn_index}`}>{turn.payload?.kind ?? "?"}</span>
      <span data-testid={`turn-query-${turn.turn_index}`}>{turn.query}</span>
    </div>
  ),
}));

// Hooks — stubbed so tests drive the exact data shape per scenario.
const mockUseAuth = vi.fn();
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => mockUseAuth() }));

const mockUseProfile = vi.fn();
vi.mock("@/hooks/useProfile", () => ({ useProfile: () => mockUseProfile() }));

const mockUseNicheTaxonomy = vi.fn();
vi.mock("@/hooks/useNicheTaxonomy", () => ({
  useNicheTaxonomy: () => mockUseNicheTaxonomy(),
}));

const mockUseAnswerSessionsList = vi.fn();
const mockUseAnswerSessionDetail = vi.fn();
vi.mock("@/hooks/useAnswerSessionQueries", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useAnswerSessionQueries")>(
    "@/hooks/useAnswerSessionQueries",
  );
  return {
    ...actual,
    useAnswerSessionsList: (...args: unknown[]) => mockUseAnswerSessionsList(...args),
    useAnswerSessionDetail: (...args: unknown[]) => mockUseAnswerSessionDetail(...args),
  };
});

const mockStream = vi.fn();
vi.mock("@/hooks/useSessionStream", () => ({
  useSessionStream: () => ({
    stream: mockStream,
    status: "idle",
    text: "",
    streamId: null,
    lastSeq: 0,
    error: null,
    stepEvents: [],
    finalPayload: null,
    abort: vi.fn(),
    reset: vi.fn(),
  }),
}));

// Ordered after mocks (per Vitest hoist rules).
const AnswerScreen = (await import("./AnswerScreen")).default;

// ── Helpers ────────────────────────────────────────────────────────────────
function makeSession(overrides: Partial<AnswerSessionRow> = {}): AnswerSessionRow & {
  title: string | null;
  initial_q: string;
} {
  return {
    id: "sess-abc",
    user_id: "user-1",
    title: null,
    initial_q: "câu hỏi mẫu",
    intent_type: "follow_up_unclassifiable",
    format: "generic",
    niche_id: null,
    ...overrides,
  };
}

function makeTurn(overrides: Partial<AnswerTurnRow> = {}): AnswerTurnRow {
  return {
    id: "turn-1",
    session_id: "sess-abc",
    turn_index: 0,
    kind: "primary",
    query: "câu hỏi mẫu",
    payload: { kind: "generic", report: { tldr: "x" } } as unknown as ReportV1,
    ...overrides,
  };
}

function renderScreen(initialPath = "/app/answer") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AnswerScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────
describe("AnswerScreen state transitions", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: { id: "user-1" },
      session: { user: { id: "user-1" } },
      loading: false,
    });
    mockUseProfile.mockReturnValue({ data: { primary_niche: null } });
    mockUseNicheTaxonomy.mockReturnValue({ data: [] });
    mockUseAnswerSessionsList.mockReturnValue({
      data: { sessions: [], next_cursor: null },
      isLoading: false,
    });
    mockUseAnswerSessionDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockStream.mockReset();
  });
  afterEach(cleanup);

  it("shows the empty prompt when there is no session and no seed query", () => {
    renderScreen("/app/answer");
    expect(screen.getByText(/Dán câu hỏi từ Studio/)).toBeTruthy();
  });

  it("renders each turn via the ContinuationTurn dispatcher when detail has turns", () => {
    mockUseAnswerSessionDetail.mockReturnValue({
      data: {
        session: makeSession({ title: "Phân tích nhịp đăng bài" }),
        turns: [
          makeTurn({ turn_index: 0, query: "câu hỏi chính", kind: "primary" }),
          makeTurn({
            id: "turn-2",
            turn_index: 1,
            kind: "timing",
            query: "giờ nào tốt?",
            payload: { kind: "timing", report: {} } as unknown as ReportV1,
          }),
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen("/app/answer?session=sess-abc");

    expect(screen.getByTestId("turn-0")).toBeTruthy();
    expect(screen.getByTestId("turn-1")).toBeTruthy();
    expect(screen.getByTestId("turn-kind-0").textContent).toBe("generic");
    expect(screen.getByTestId("turn-kind-1").textContent).toBe("timing");
    expect(screen.getByTestId("turn-query-1").textContent).toBe("giờ nào tốt?");
  });

  it("surfaces the 'Chưa có lượt' diagnostic card when detail is ready but turns are empty, and the refetch button calls detailQuery.refetch", () => {
    const refetch = vi.fn();
    mockUseAnswerSessionDetail.mockReturnValue({
      data: { session: makeSession(), turns: [] },
      isLoading: false,
      isError: false,
      refetch,
    });
    renderScreen("/app/answer?session=sess-abc");

    expect(screen.getByText(/Chưa có lượt trong phiên này/)).toBeTruthy();
    const retry = screen.getByRole("button", { name: /Tải lại phiên/ });
    fireEvent.click(retry);
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders the detail-load error banner when the session fetch errored and a sessionId is present", () => {
    mockUseAnswerSessionDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("http_500"),
      refetch: vi.fn(),
    });
    renderScreen("/app/answer?session=sess-abc");
    // HTTP-tagged error renders the "Server trả lỗi" copy.
    expect(screen.getByText(/Server trả lỗi \(HTTP 500\)/)).toBeTruthy();
  });

  it("renders the session-not-found banner when the detail fetch 404s", () => {
    const notFound = new Error("session_not_found");
    notFound.name = "SessionNotFound";
    mockUseAnswerSessionDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: notFound,
      refetch: vi.fn(),
    });
    renderScreen("/app/answer?session=sess-abc");
    expect(screen.getByText(/Phiên không tồn tại/)).toBeTruthy();
  });

  it("disables the follow-up composer until a sessionId is in the URL", () => {
    renderScreen("/app/answer");
    const composer = screen.getByTestId("follow-up-composer");
    expect(composer.getAttribute("data-disabled")).toBe("true");
  });

  it("enables the follow-up composer once a sessionId is in the URL", () => {
    mockUseAnswerSessionDetail.mockReturnValue({
      data: { session: makeSession(), turns: [makeTurn()] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen("/app/answer?session=sess-abc");
    const composer = screen.getByTestId("follow-up-composer");
    expect(composer.getAttribute("data-disabled")).toBe("false");
  });
});
