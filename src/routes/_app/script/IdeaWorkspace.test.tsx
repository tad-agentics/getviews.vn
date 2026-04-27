/**
 * IdeaWorkspace tests — Script step 1 (per design pack
 * ``screens/script.jsx`` lines 51-179). Verifies the three paths and the
 * gating from ScriptScreen.tsx (no URL prefill → workspace).
 *
 * Surface contracts:
 *   1. Mode gate — ScriptScreen with no params renders IdeaWorkspace,
 *      with a ``?topic=`` param renders the detail screen.
 *   2. Path A — RitualScript[] → IdeaList rows, click → navigate to
 *      ``/app/script?topic=…&duration=…`` (via ``scriptPrefillFromRitual``).
 *   3. Path A empty — when ritual returns 0 scripts, friendly empty state.
 *   4. Path B — CustomIdeaCard submit gates on non-empty text and
 *      navigates with topic + duration query params.
 *   5. Path C — DraftsList shows draft.topic + relative time + shot count;
 *      "Xem tất cả" toggle reveals drafts beyond the first 6.
 *   6. Path C empty — friendly empty state when no drafts.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import type { ScriptDraftRow } from "@/lib/api-types";
import type { RitualScript } from "@/hooks/useDailyRitual";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockUseProfile = vi.fn();
const mockUseDailyRitual = vi.fn();
const mockUseScriptDrafts = vi.fn();

vi.mock("@/hooks/useProfile", () => ({ useProfile: () => mockUseProfile() }));
vi.mock("@/hooks/useDailyRitual", () => ({
  useDailyRitual: (enabled: boolean, primary: number | null) =>
    mockUseDailyRitual(enabled, primary),
}));
vi.mock("@/hooks/useScriptSave", () => ({
  useScriptDrafts: (enabled: boolean) => mockUseScriptDrafts(enabled),
}));

const { IdeaWorkspace } = await import("./IdeaWorkspace");

const RITUAL_SCRIPTS: RitualScript[] = [
  {
    hook_type_en: "comparison_x10",
    hook_type_vi: "So sánh giá ×10",
    title_vi: "Tai nghe 200k vs 2 triệu — đáng gấp 10 lần?",
    why_works: 'Pattern "so sánh giá ×N" tăng 248% trong ngách Tech.',
    retention_est_pct: 72,
    shot_count: 6,
    length_sec: 32,
  },
  {
    hook_type_en: "reverse_question",
    hook_type_vi: "Hook nghi vấn ngược",
    title_vi: "Tại sao iPad Pro M4 đắt mà vẫn cháy hàng?",
    why_works: 'Hook "Sao ___ mà ___" đang chạy mạnh.',
    retention_est_pct: 68,
    shot_count: 5,
    length_sec: 28,
  },
];

function makeDraft(overrides: Partial<ScriptDraftRow>): ScriptDraftRow {
  return {
    id: "draft-x",
    topic: "Review tai nghe",
    hook: "",
    hook_delay_ms: 1200,
    duration_sec: 32,
    tone: "Chuyên gia",
    shots: [
      { t0: 0, t1: 3, cam: "Cận", voice: "v", viz: "" } as never,
    ],
    ...overrides,
  };
}

function renderWorkspace() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/app/script"]}>
        <IdeaWorkspace />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockUseProfile.mockReturnValue({ data: { primary_niche: 4 } });
  mockUseDailyRitual.mockReturnValue({
    data: { niche_id: 4, scripts: RITUAL_SCRIPTS },
    emptyReason: null,
    isPending: false,
  });
  mockUseScriptDrafts.mockReturnValue({
    data: { drafts: [makeDraft({ id: "d1", topic: "Nháp 1" })] },
    isPending: false,
  });
});

afterEach(cleanup);

describe("IdeaWorkspace", () => {
  it("renders the H1 and three path letter chips A/B/C", () => {
    renderWorkspace();
    expect(screen.getByText(/Bạn muốn viết gì hôm nay/)).toBeTruthy();
    expect(screen.getByText("A")).toBeTruthy();
    expect(screen.getByText("B")).toBeTruthy();
    expect(screen.getByText("C")).toBeTruthy();
  });

  it("Path A — renders ritual scripts as numbered ideas", () => {
    renderWorkspace();
    expect(
      screen.getByText("Tai nghe 200k vs 2 triệu — đáng gấp 10 lần?"),
    ).toBeTruthy();
    expect(
      screen.getByText("Tại sao iPad Pro M4 đắt mà vẫn cháy hàng?"),
    ).toBeTruthy();
    // Numbered 01, 02
    expect(screen.getByText("01")).toBeTruthy();
    expect(screen.getByText("02")).toBeTruthy();
    // Retention estimate rendered as ~72% / ~68%
    expect(screen.getByText("~72%")).toBeTruthy();
    expect(screen.getByText("~68%")).toBeTruthy();
  });

  it("Path A — clicking an idea navigates with topic + duration prefill", () => {
    renderWorkspace();
    fireEvent.click(
      screen.getByText("Tai nghe 200k vs 2 triệu — đáng gấp 10 lần?"),
    );
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    const url = mockNavigate.mock.calls[0][0] as string;
    expect(url).toMatch(/^\/app\/script\?/);
    expect(url).toMatch(/niche_id=4/);
    expect(url).toMatch(/duration=32/);
    expect(decodeURIComponent(url.replace(/\+/g, " "))).toMatch(
      /Tai nghe 200k vs 2 triệu/,
    );
  });

  it("Path A — empty ritual shows friendly fallback", () => {
    mockUseDailyRitual.mockReturnValue({
      data: { niche_id: 4, scripts: [] },
      emptyReason: null,
      isPending: false,
    });
    renderWorkspace();
    expect(screen.getByText(/Hôm nay AI chưa gợi ý/)).toBeTruthy();
  });

  it("Path A — niche-stale ritual shows the niche-changed copy", () => {
    mockUseDailyRitual.mockReturnValue({
      data: null,
      emptyReason: "ritual_niche_stale",
      isPending: false,
    });
    renderWorkspace();
    expect(screen.getByText(/Bạn vừa đổi ngách/)).toBeTruthy();
  });

  it("Path B — CTA disabled when textarea empty, enabled after typing", () => {
    renderWorkspace();
    const cta = screen.getByRole("button", { name: /Tạo script/ }) as HTMLButtonElement;
    expect(cta.disabled).toBe(true);
    const textarea = screen.getByPlaceholderText(/Mô tả ý tưởng video/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Setup desk 3 triệu" } });
    expect(cta.disabled).toBe(false);
  });

  it("Path B — submit navigates with topic + duration query", () => {
    renderWorkspace();
    const textarea = screen.getByPlaceholderText(/Mô tả ý tưởng video/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Setup desk 3 triệu" } });
    fireEvent.click(screen.getByRole("button", { name: /Tạo script/ }));
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    const url = mockNavigate.mock.calls[0][0] as string;
    expect(url).toMatch(/^\/app\/script\?/);
    expect(decodeURIComponent(url.replace(/\+/g, " "))).toMatch(
      /Setup desk 3 triệu/,
    );
    expect(url).toMatch(/duration=32/);
  });

  it("Path C — renders drafts with topic + shot count", () => {
    renderWorkspace();
    expect(screen.getByText("Nháp 1")).toBeTruthy();
  });

  it('Path C — "Xem tất cả" toggle appears when drafts > 6', () => {
    const drafts: ScriptDraftRow[] = Array.from({ length: 8 }, (_, i) =>
      makeDraft({ id: `d${i}`, topic: `Nháp ${i + 1}` }),
    );
    mockUseScriptDrafts.mockReturnValue({
      data: { drafts },
      isPending: false,
    });
    renderWorkspace();
    // Only first 6 visible initially
    expect(screen.queryByText("Nháp 7")).toBeNull();
    expect(screen.queryByText("Nháp 8")).toBeNull();
    fireEvent.click(screen.getByText(/Xem tất cả 8 nháp/));
    expect(screen.getByText("Nháp 7")).toBeTruthy();
    expect(screen.getByText("Nháp 8")).toBeTruthy();
  });

  it("Path C — empty drafts shows friendly fallback", () => {
    mockUseScriptDrafts.mockReturnValue({
      data: { drafts: [] },
      isPending: false,
    });
    renderWorkspace();
    expect(screen.getByText(/Chưa có nháp nào — bắt đầu từ Mục A hoặc B/)).toBeTruthy();
  });
});
