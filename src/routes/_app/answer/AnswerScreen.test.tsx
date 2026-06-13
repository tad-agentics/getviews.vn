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
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router";

import type { AnswerSessionRow, AnswerTurnRow, ReportV1 } from "@/lib/api-types";
import { createAnswerSession } from "@/lib/answerApi";
import { savePendingAnswerStream } from "@/lib/sseResume";

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
vi.mock("@/components/v2/TopBar", () => ({
  TopBar: () => <div data-testid="top-bar" />,
}));
vi.mock("@/components/v2/Btn", () => ({
  Btn: ({ children, ...rest }: { children?: React.ReactNode }) => (
    <button type="button" {...rest}>
      {children}
    </button>
  ),
}));
vi.mock("@/components/v2/answer/FollowUpComposer", () => ({
  FollowUpComposer: ({
    disabled,
    value,
    onChange,
    onSubmit,
    variant,
  }: {
    disabled?: boolean;
    value: string;
    onChange: (v: string) => void;
    onSubmit: () => void;
    variant?: string;
  }) => (
    <div
      data-testid="follow-up-composer"
      data-disabled={String(disabled ?? false)}
      data-variant={variant ?? "initial"}
    >
      <textarea
        data-testid="composer-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <button type="button" data-testid="composer-submit" disabled={disabled} onClick={onSubmit}>
        Gửi
      </button>
    </div>
  ),
}));
vi.mock("@/components/v2/answer/IntentCtaRail", () => ({
  IntentCtaRail: ({
    disabled,
    onCta,
  }: {
    disabled?: boolean;
    onCta: (s: { id: string; intentType: string }, q: string) => void;
  }) => (
    <div data-testid="intent-cta-rail" data-disabled={String(disabled ?? false)}>
      <button
        type="button"
        data-testid="cta-script"
        disabled={disabled}
        onClick={() =>
          onCta({ id: "video_script", intentType: "shot_list" }, "Tạo kịch bản từ kết quả")
        }
      >
        Tạo kịch bản
      </button>
    </div>
  ),
}));
vi.mock("@/components/v2/answer/ResearchStrip", () => ({
  LivePipelineStrip: () => null,
  useResearchStage: () => 0,
  // Phase 5.7.1 — AnswerScreen calls this to suppress LivePipelineStrip
  // on cache-hit pattern. Mocked to return false so the test renders
  // the live-strip path (or, in these tests, just nothing).
  isCacheHitPattern: () => false,
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

const mockUseAnswerSessionDetail = vi.fn();
vi.mock("@/hooks/useAnswerSessionQueries", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useAnswerSessionQueries")>(
    "@/hooks/useAnswerSessionQueries",
  );
  return {
    ...actual,
    useAnswerSessionDetail: (...args: unknown[]) => mockUseAnswerSessionDetail(...args),
  };
});

const mockStream = vi.fn();
const mockResetStream = vi.fn();
let mockStreamStatus: "idle" | "streaming" | "done" | "error" = "idle";
vi.mock("@/hooks/useSessionStream", () => ({
  useSessionStream: () => ({
    stream: mockStream,
    status: mockStreamStatus,
    text: "",
    streamId: null,
    lastSeq: 0,
    error: null,
    steps: [],
    heartbeatCount: 0,
    finalPayload: null,
    preSynthesisData: null,
    channelContext: null,
    narrativeReady: null,
    heartbeatElapsedSec: 0,
    abort: vi.fn(),
    reset: mockResetStream,
  }),
}));

// Ordered after mocks (per Vitest hoist rules).
const AnswerScreen = (await import("./AnswerScreen")).default;

const mockCreateAnswerSession = vi.mocked(createAnswerSession);

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
    mockUseProfile.mockReturnValue({ data: { creator_niche_id: null } });
    mockUseNicheTaxonomy.mockReturnValue({ data: [] });
    mockUseAnswerSessionDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockStream.mockReset();
    mockCreateAnswerSession.mockReset();
    mockStreamStatus = "idle";
  });
  afterEach(cleanup);

  it("shows initial composer on blank landing without fake hero question", () => {
    renderScreen("/app/answer");
    const composer = screen.getByTestId("follow-up-composer");
    expect(composer.getAttribute("data-variant")).toBe("initial");
    expect(screen.queryByText(/Xu hướng đang hot/)).toBeNull();
    expect(screen.queryByText(/Dán câu hỏi từ Studio/)).toBeNull();
    expect(screen.getByTestId("header").textContent?.trim()).toBe("");
  });

  it("hides start composer while stream is in flight with zero turns", () => {
    mockStreamStatus = "streaming";
    mockUseAnswerSessionDetail.mockReturnValue({
      data: {
        session: makeSession({ id: "sess-stream", initial_q: "https://tiktok.com/@a/video/1" }),
        turns: [],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen("/app/answer?session=sess-stream");
    expect(screen.queryByTestId("follow-up-composer")).toBeNull();
  });

  it("hides start composer on ?q= bootstrap before session id lands", () => {
    mockStreamStatus = "streaming";
    mockStream.mockReturnValue(new Promise(() => {}));
    mockCreateAnswerSession.mockResolvedValue({
      id: "new-sess",
      user_id: "user-1",
      title: null,
      initial_q: "https://www.tiktok.com/@a/video/1",
      intent_type: "video_diagnosis",
      format: "video",
      niche_id: null,
    });
    renderScreen("/app/answer?q=https://www.tiktok.com/@a/video/1");
    expect(screen.queryByTestId("follow-up-composer")).toBeNull();
  });

  it("hides start composer while stream is done but turn not persisted yet", () => {
    mockStreamStatus = "done";
    mockUseAnswerSessionDetail.mockReturnValue({
      data: {
        session: makeSession({ id: "sess-done", initial_q: "https://tiktok.com/@a/video/1" }),
        turns: [],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen("/app/answer?session=sess-done");
    expect(screen.queryByTestId("follow-up-composer")).toBeNull();
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

  it("enables the composer on blank /app/answer so a new question can start (Cloud Run + user present)", () => {
    renderScreen("/app/answer");
    const composer = screen.getByTestId("follow-up-composer");
    expect(composer.getAttribute("data-disabled")).toBe("false");
  });

  it("clears composer text after submitting a new query (no session)", async () => {
    mockCreateAnswerSession.mockResolvedValue({
      id: "new-sess",
      user_id: "user-1",
      title: null,
      initial_q: "Xu hướng test",
      intent_type: "follow_up_unclassifiable",
      format: "generic",
      niche_id: null,
    });
    mockStream.mockResolvedValue({
      ok: true,
      finalPayload: {
        kind: "generic",
        report: { tldr: "ok", related_questions: [] },
      } as unknown as ReportV1,
    });

    renderScreen("/app/answer");
    const input = screen.getByTestId("composer-input") as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: "Xu hướng test" } });
    fireEvent.click(screen.getByTestId("composer-submit"));

    await waitFor(() => {
      expect(input.value).toBe("");
    });
  });

  it("restores composer text when the initial stream fails after submit", async () => {
    mockCreateAnswerSession.mockResolvedValue({
      id: "new-sess",
      user_id: "user-1",
      title: null,
      initial_q: "my query",
      intent_type: "follow_up_unclassifiable",
      format: "generic",
      niche_id: null,
    });
    mockStream.mockResolvedValue({ ok: false, error: "stream_failed" });

    renderScreen("/app/answer");
    const input = screen.getByTestId("composer-input") as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: "my query" } });
    fireEvent.click(screen.getByTestId("composer-submit"));

    await waitFor(() => {
      expect(input.value).toBe("");
    });

    await waitFor(() => {
      const restored = screen.getByTestId("composer-input") as HTMLTextAreaElement;
      expect(restored.value).toBe("my query");
    });
  });

  it("blocks bare non-TikTok video URL on ?q= bootstrap without creating a session", async () => {
    const fakeQ = "linhbeauty.vn/video/74012345678901234";
    const router = createMemoryRouter(
      [{ path: "/app/answer", element: <AnswerScreen /> }],
      {
        initialEntries: [
          `/app/answer?q=${encodeURIComponent(fakeQ)}&mode=flop`,
        ],
      },
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent ?? "").toMatch(/link TikTok/i);
    });
    expect(mockCreateAnswerSession).not.toHaveBeenCalled();
    expect(screen.queryByTestId("resume-stream-btn")).toBeNull();
  });

  it("keeps session in URL and shows resume when bootstrap stream fails on ?q=", async () => {
    const tiktokQ = "https://www.tiktok.com/@creator/video/7123456789";
    mockCreateAnswerSession.mockResolvedValue({
      id: "new-sess",
      user_id: "user-1",
      title: null,
      initial_q: tiktokQ,
      intent_type: "video_diagnosis",
      format: "video",
      niche_id: null,
    });
    mockStream.mockResolvedValue({ ok: false, error: "stream_failed" });
    savePendingAnswerStream({
      sessionId: "new-sess",
      streamId: "sid-1",
      seq: 1,
      query: tiktokQ,
      turnKind: "primary",
      startedAt: Date.now(),
      creditsUsed: 2,
      sessionFormat: "video",
    });
    mockUseAnswerSessionDetail.mockImplementation((id: string | null | undefined) => ({
      data:
        id === "new-sess"
          ? { session: makeSession({ id: "new-sess", initial_q: tiktokQ, format: "video" }), turns: [] }
          : undefined,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }));

    const router = createMemoryRouter(
      [{ path: "/app/answer", element: <AnswerScreen /> }],
      { initialEntries: [`/app/answer?q=${encodeURIComponent(tiktokQ)}&mode=win`] },
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(router.state.location.search).toContain("session=new-sess");
    });
    expect(screen.getByTestId("resume-stream-btn")).toBeTruthy();
    expect(screen.queryByTestId("error-retry-btn")).toBeNull();
  });

  it("does not show Gửi lại for insufficient_credits (banner only)", async () => {
    const tiktokQ = "https://www.tiktok.com/@creator/video/777";
    mockCreateAnswerSession.mockResolvedValue({
      id: "no-credit-sess",
      user_id: "user-1",
      title: null,
      initial_q: tiktokQ,
      intent_type: "video_diagnosis",
      format: "video",
      niche_id: null,
    });
    mockStream.mockResolvedValue({ ok: false, error: "insufficient_credits" });
    mockUseAnswerSessionDetail.mockReturnValue({
      data: {
        session: makeSession({ id: "no-credit-sess", initial_q: tiktokQ, format: "video" }),
        turns: [],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    const router = createMemoryRouter(
      [{ path: "/app/answer", element: <AnswerScreen /> }],
      { initialEntries: [`/app/answer?q=${encodeURIComponent(tiktokQ)}`] },
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Không đủ credit/i)).toBeTruthy();
    });
    expect(screen.queryByTestId("error-retry-btn")).toBeNull();
    expect(screen.queryByTestId("resume-stream-btn")).toBeNull();
  });

  it("clears stale stream error when navigating to a completed session", async () => {
    const failQ = "https://www.tiktok.com/@creator/video/111";
    mockCreateAnswerSession.mockResolvedValue({
      id: "fail-sess",
      user_id: "user-1",
      title: null,
      initial_q: failQ,
      intent_type: "video_diagnosis",
      format: "video",
      niche_id: null,
    });
    mockStream.mockResolvedValue({ ok: false, error: "stream_failed" });

    const router = createMemoryRouter(
      [{ path: "/app/answer", element: <AnswerScreen /> }],
      { initialEntries: [`/app/answer?q=${encodeURIComponent(failQ)}`] },
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Kết nối streaming bị ngắt/)).toBeTruthy();
    });

    mockUseAnswerSessionDetail.mockReturnValue({
      data: {
        session: makeSession({ id: "done-sess", format: "video" }),
        turns: [makeTurn({ session_id: "done-sess", payload: { kind: "video", report: {} } as ReportV1 })],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    await router.navigate(`/app/answer?session=done-sess`);

    await waitFor(() => {
      expect(screen.queryByText(/Kết nối streaming bị ngắt/)).toBeNull();
    });
    expect(screen.getByTestId("turn-0")).toBeTruthy();
    expect(mockResetStream).toHaveBeenCalled();
  });

  it("does not show resume button when stream fails without replay handles", async () => {
    const tiktokQ = "https://www.tiktok.com/@creator/video/999";
    mockCreateAnswerSession.mockResolvedValue({
      id: "new-sess-2",
      user_id: "user-1",
      title: null,
      initial_q: tiktokQ,
      intent_type: "video_diagnosis",
      format: "video",
      niche_id: null,
    });
    mockStream.mockResolvedValue({ ok: false, error: "stream_failed" });
    mockUseAnswerSessionDetail.mockReturnValue({
      data: { session: makeSession({ id: "new-sess-2", initial_q: tiktokQ }), turns: [] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    const router = createMemoryRouter(
      [{ path: "/app/answer", element: <AnswerScreen /> }],
      { initialEntries: [`/app/answer?q=${encodeURIComponent(tiktokQ)}`] },
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(router.state.location.search).toContain("session=new-sess-2");
    });
    expect(screen.queryByTestId("resume-stream-btn")).toBeNull();
    expect(screen.getByTestId("error-retry-btn")).toBeTruthy();
    expect(screen.getByText(/Bấm Gửi lại/)).toBeTruthy();
  });

  it("retries primary stream when error-retry is clicked after bootstrap failure", async () => {
    const tiktokQ = "https://www.tiktok.com/@creator/video/888";
    mockCreateAnswerSession.mockResolvedValue({
      id: "retry-sess",
      user_id: "user-1",
      title: null,
      initial_q: tiktokQ,
      intent_type: "video_diagnosis",
      format: "video",
      niche_id: null,
    });
    mockStream
      .mockResolvedValueOnce({ ok: false, error: "stream_failed" })
      .mockResolvedValueOnce({ ok: true, finalPayload: { kind: "video", report: {} } });
    mockUseAnswerSessionDetail.mockReturnValue({
      data: { session: makeSession({ id: "retry-sess", initial_q: tiktokQ, format: "video" }), turns: [] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    const router = createMemoryRouter(
      [{ path: "/app/answer", element: <AnswerScreen /> }],
      { initialEntries: [`/app/answer?q=${encodeURIComponent(tiktokQ)}`] },
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("error-retry-btn")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("error-retry-btn"));
    await waitFor(() => {
      expect(mockStream).toHaveBeenCalledTimes(2);
    });
    const retryCall = mockStream.mock.calls[1]?.[0];
    expect(retryCall?.sourceEntry).toBe("error_retry_ui");
  });

  it("retries primary stream from composer when session exists with zero turns", async () => {
    mockStream.mockResolvedValue({ ok: true, finalPayload: { kind: "generic", report: {} } });
    mockUseAnswerSessionDetail.mockReturnValue({
      data: {
        session: makeSession({ id: "sess-abc", initial_q: "my failed query" }),
        turns: [],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderScreen("/app/answer?session=sess-abc");
    const input = screen.getByTestId("composer-input") as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: "my failed query" } });
    fireEvent.click(screen.getByTestId("composer-submit"));

    await waitFor(() => {
      expect(mockStream).toHaveBeenCalled();
    });
    expect(mockStream.mock.calls[0]?.[0]?.sourceEntry).toBe("error_retry_ui");
  });

  it("renders invalid_payload copy when create session fails with FastAPI validation JSON", async () => {
    mockCreateAnswerSession.mockRejectedValue(
      new Error(
        JSON.stringify({
          detail: [
            {
              type: "literal_error",
              loc: ["body", "format"],
              msg: "Input should be ...",
              input: "script",
            },
          ],
        }),
      ),
    );
    renderScreen("/app/answer?q=viết kịch bản");
    await waitFor(() => {
      expect(screen.getByText(/Dữ liệu gửi lên không hợp lệ/)).toBeTruthy();
    });
  });

  it("shows IntentCtaRail without duplicate follow-up composer when session has turns", () => {
    mockUseAnswerSessionDetail.mockReturnValue({
      data: { session: makeSession({ format: "video" }), turns: [makeTurn()] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen("/app/answer?session=sess-abc");
    expect(screen.getByTestId("intent-cta-rail")).toBeTruthy();
    expect(screen.queryByTestId("follow-up-composer")).toBeNull();
  });

  it("appends a follow-up turn from IntentCtaRail when session already has turns", async () => {
    mockStream.mockResolvedValue({ ok: true, finalPayload: { kind: "generic", report: {} } });
    mockUseAnswerSessionDetail.mockReturnValue({
      data: {
        session: makeSession({ id: "sess-abc", format: "generic" }),
        turns: [makeTurn()],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderScreen("/app/answer?session=sess-abc");
    fireEvent.click(screen.getByTestId("cta-script"));

    await waitFor(() => {
      expect(mockStream).toHaveBeenCalled();
    });
    expect(mockStream.mock.calls[0]?.[0]?.mode).toBe("answer_turn");
  });

  it("shows initial composer when no session is active", () => {
    renderScreen("/app/answer");
    const composer = screen.getByTestId("follow-up-composer");
    expect(composer.getAttribute("data-variant")).toBe("initial");
  });
});
