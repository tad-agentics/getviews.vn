/**
 * Phase D.2.4 — HistoryScreen pagination + cross-type search tests.
 *
 * Mocks every hook that would otherwise touch Supabase:
 *   - useAuth (session present).
 *   - useHistoryUnion as useInfiniteQuery-shape (pages + hasNextPage +
 *     fetchNextPage mock).
 *   - useSearchHistoryUnion as useQuery-shape returning HistoryUnionRow[].
 *   - useDeleteSession / useUpdateSession as inert mutations.
 *   - AppLayout as a passthrough.
 *
 * jsdom doesn't ship IntersectionObserver — we stub the constructor and
 * trigger callbacks manually per test.
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import type { HistoryUnionRow } from "@/hooks/useHistoryUnion";

// ── Mocks ─────────────────────────────────────────────────────────────────

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

vi.mock("@/lib/logUsage", () => ({ logUsage: vi.fn() }));

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockUseAuth = vi.fn();
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => mockUseAuth() }));

const mockUseHistoryUnion = vi.fn();
const mockUseSearchHistoryUnion = vi.fn();
vi.mock("@/hooks/useHistoryUnion", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useHistoryUnion")>(
    "@/hooks/useHistoryUnion",
  );
  return {
    ...actual,
    useHistoryUnion: (...args: unknown[]) => mockUseHistoryUnion(...args),
    useSearchHistoryUnion: (...args: unknown[]) => mockUseSearchHistoryUnion(...args),
  };
});

vi.mock("@/hooks/useChatSessions", () => ({
  useDeleteSession: () => ({ mutateAsync: vi.fn() }),
  useUpdateSession: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/useAnswerSessionQueries", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useAnswerSessionQueries")>(
    "@/hooks/useAnswerSessionQueries",
  );
  return {
    ...actual,
    useArchiveAnswerSession: () => ({ mutateAsync: vi.fn() }),
    useRenameAnswerSession: () => ({ mutateAsync: vi.fn() }),
  };
});

// IntersectionObserver stub — register callbacks so tests can trigger them.
const ioInstances: Array<{
  cb: IntersectionObserverCallback;
  observe: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
}> = [];
beforeEach(() => {
  ioInstances.length = 0;
  (globalThis as unknown as { IntersectionObserver: typeof IntersectionObserver }).IntersectionObserver = class {
    readonly cb: IntersectionObserverCallback;
    observe = vi.fn();
    disconnect = vi.fn();
    unobserve = vi.fn();
    takeRecords = vi.fn(() => [] as IntersectionObserverEntry[]);
    root: Element | Document | null = null;
    rootMargin = "";
    thresholds: ReadonlyArray<number> = [];
    constructor(cb: IntersectionObserverCallback) {
      this.cb = cb;
      ioInstances.push({ cb: this.cb, observe: this.observe, disconnect: this.disconnect });
    }
  } as unknown as typeof IntersectionObserver;
});

const HistoryScreen = (await import("./HistoryScreen")).default;

// ── Helpers ───────────────────────────────────────────────────────────────

function makeRow(overrides: Partial<HistoryUnionRow> = {}): HistoryUnionRow {
  return {
    id: overrides.id ?? "row-1",
    type: overrides.type ?? "answer",
    format: overrides.format ?? "pattern",
    niche_id: overrides.niche_id ?? 3,
    title: overrides.title ?? "Research session 1",
    turn_count: overrides.turn_count ?? 2,
    updated_at: overrides.updated_at ?? new Date().toISOString(),
  };
}

function mockInfiniteQuery({
  pages,
  hasNextPage = false,
  isFetchingNextPage = false,
  isLoading = false,
  isError = false,
}: {
  pages: HistoryUnionRow[][];
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  isLoading?: boolean;
  isError?: boolean;
}) {
  return {
    data: { pages, pageParams: pages.map((_, i) => (i === 0 ? null : `cursor-${i}`)) },
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    isFetching: isLoading || isFetchingNextPage,
    fetchNextPage: vi.fn(),
    refetch: vi.fn(),
  };
}

function renderScreen(searchInit = "") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/app/history${searchInit}`]}>
        <HistoryScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────

describe("HistoryScreen — D.2.4 pagination + search", () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
    mockUseHistoryUnion.mockReset();
    mockUseSearchHistoryUnion.mockReset();
    mockUseAuth.mockReturnValue({
      user: { id: "u" },
      session: { user: { id: "u" } },
      loading: false,
      signOut: vi.fn(),
    });
    mockUseSearchHistoryUnion.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
  });
  afterEach(cleanup);

  it("renders rows from the first page of useHistoryUnion", () => {
    mockUseHistoryUnion.mockReturnValue(
      mockInfiniteQuery({
        pages: [[makeRow({ id: "a", title: "Answer A" }), makeRow({ id: "b", title: "Chat B", type: "chat" })]],
      }),
    );
    renderScreen();
    expect(screen.getByText(/Answer A/)).toBeTruthy();
    expect(screen.getByText(/Chat B/)).toBeTruthy();
  });

  it("renders the loading sentinel only while isFetchingNextPage + hasNextPage", () => {
    mockUseHistoryUnion.mockReturnValue(
      mockInfiniteQuery({
        pages: [[makeRow()]],
        hasNextPage: true,
        isFetchingNextPage: true,
      }),
    );
    renderScreen();
    expect(screen.getByText(/Đang tải thêm…/)).toBeTruthy();
  });

  it("does not render the sentinel when hasNextPage is false", () => {
    mockUseHistoryUnion.mockReturnValue(
      mockInfiniteQuery({ pages: [[makeRow()]], hasNextPage: false }),
    );
    renderScreen();
    expect(screen.queryByText(/Đang tải thêm/)).toBeNull();
  });

  it("triggers fetchNextPage when the sentinel intersects + hasNextPage", async () => {
    const query = mockInfiniteQuery({
      pages: [[makeRow({ id: "a" }), makeRow({ id: "b" })]],
      hasNextPage: true,
    });
    mockUseHistoryUnion.mockReturnValue(query);
    renderScreen();
    // Sentinel registration happens during render — IO constructor fires.
    await waitFor(() => {
      expect(ioInstances.length).toBeGreaterThan(0);
    });
    const io = ioInstances[0];
    act(() => {
      io.cb(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });
    expect(query.fetchNextPage).toHaveBeenCalledTimes(1);
  });

  it("skips fetchNextPage when isFetchingNextPage is already true", async () => {
    const query = mockInfiniteQuery({
      pages: [[makeRow()]],
      hasNextPage: true,
      isFetchingNextPage: true,
    });
    mockUseHistoryUnion.mockReturnValue(query);
    renderScreen();
    await waitFor(() => expect(ioInstances.length).toBeGreaterThan(0));
    const io = ioInstances[0];
    act(() => {
      io.cb(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });
    expect(query.fetchNextPage).not.toHaveBeenCalled();
  });

  it("uses useSearchHistoryUnion when the search input is non-empty", async () => {
    mockUseHistoryUnion.mockReturnValue(
      mockInfiniteQuery({ pages: [[makeRow({ id: "paged", title: "Paged row" })]] }),
    );
    mockUseSearchHistoryUnion.mockReturnValue({
      data: [makeRow({ id: "searched", title: "Searched row", type: "answer" })],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen();

    const input = screen.getByPlaceholderText(/Tìm trong hội thoại cũ/);
    fireEvent.change(input, { target: { value: "bass" } });

    // Debounced 300ms — wait it out.
    await waitFor(
      () => {
        expect(screen.queryByText(/Searched row/)).toBeTruthy();
      },
      { timeout: 1500 },
    );
    // Paged rows hide while searching.
    expect(screen.queryByText(/Paged row/)).toBeNull();
  });

  it("renders the empty-search copy when search returns zero rows", async () => {
    mockUseHistoryUnion.mockReturnValue(mockInfiniteQuery({ pages: [[]] }));
    mockUseSearchHistoryUnion.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    renderScreen();
    const input = screen.getByPlaceholderText(/Tìm trong hội thoại cũ/);
    fireEvent.change(input, { target: { value: "nope" } });
    await waitFor(
      () => {
        expect(screen.queryByText(/Không tìm thấy phiên nào/)).toBeTruthy();
      },
      { timeout: 1500 },
    );
  });
});
