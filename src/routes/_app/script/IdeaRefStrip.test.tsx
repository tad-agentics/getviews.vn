/**
 * IdeaRefStrip tests — script step-2 reference strip (S3).
 * Per design pack ``screens/script.jsx`` lines 1284-1360.
 *
 * Surface contracts:
 *   1. Empty / pending state — strip hides itself entirely (no flicker).
 *   2. Headline includes the angle word and the live count.
 *   3. Each card renders match% pill, duration pill, creator handle,
 *      shot label, formatted views.
 *   4. Card with tiktok_url renders as <a target="_blank" rel="noopener">;
 *      missing tiktok_url renders as a plain <div>.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { ScriptIdeaReference } from "@/lib/api-types";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

const mockUseIdeaReferences = vi.fn();
vi.mock("@/hooks/useIdeaReferences", () => ({
  useIdeaReferences: (...args: unknown[]) => mockUseIdeaReferences(...args),
}));

const { IdeaRefStrip } = await import("./IdeaRefStrip");

function makeRef(overrides: Partial<ScriptIdeaReference> = {}): ScriptIdeaReference {
  return {
    video_id: "v1",
    creator_handle: "@huy.codes",
    tiktok_url: "https://tiktok.com/@huy.codes/video/v1",
    thumbnail_url: "https://cdn.test/thumb.jpg",
    views: 287_000,
    duration_sec: 32,
    hook_type: "question",
    shot_label: "Cùng pattern so sánh giá ×10",
    match_pct: 96,
    ...overrides,
  };
}

function renderStrip(props: { nicheId?: number | null; hookType?: string | null; ideaAngle?: string | null } = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <IdeaRefStrip
        nicheId={props.nicheId ?? 7}
        hookType={props.hookType ?? "question"}
        ideaAngle={props.ideaAngle}
      />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockUseIdeaReferences.mockReset();
});

afterEach(cleanup);

describe("IdeaRefStrip", () => {
  it("renders nothing while the query is pending", () => {
    mockUseIdeaReferences.mockReturnValue({ data: undefined, isPending: true });
    const { container } = renderStrip();
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when references are empty", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: { niche_id: 7, hook_type: "question", references: [] },
      isPending: false,
    });
    const { container } = renderStrip();
    expect(container.firstChild).toBeNull();
  });

  it("renders headline with the live count + angle word", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: {
        niche_id: 7,
        hook_type: "question",
        references: [makeRef(), makeRef({ video_id: "v2" })],
      },
      isPending: false,
    });
    renderStrip({ ideaAngle: "so sánh giá ×N" });
    expect(screen.getByText(/2 video viral cùng angle/)).toBeTruthy();
    expect(screen.getByText(/so sánh giá ×N/)).toBeTruthy();
  });

  it("falls back to 'này' when ideaAngle is empty/null", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: { niche_id: 7, hook_type: null, references: [makeRef()] },
      isPending: false,
    });
    renderStrip({ ideaAngle: null });
    expect(screen.getByText(/cùng angle .*này/)).toBeTruthy();
  });

  it("renders each card with match%, duration, creator, label, and views", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: { niche_id: 7, hook_type: "question", references: [makeRef()] },
      isPending: false,
    });
    renderStrip();
    expect(screen.getByText("96%")).toBeTruthy();
    expect(screen.getByText("32s")).toBeTruthy();
    expect(screen.getByText("@huy.codes")).toBeTruthy();
    expect(screen.getByText("Cùng pattern so sánh giá ×10")).toBeTruthy();
    expect(screen.getByText(/287\.0K view/)).toBeTruthy();
  });

  it("formats views over 1M with M suffix", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: {
        niche_id: 7,
        hook_type: null,
        references: [makeRef({ views: 1_400_000 })],
      },
      isPending: false,
    });
    renderStrip();
    expect(screen.getByText(/1\.4M view/)).toBeTruthy();
  });

  it("renders card with tiktok_url as external link", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: { niche_id: 7, hook_type: null, references: [makeRef()] },
      isPending: false,
    });
    renderStrip();
    const link = screen.getByRole("link") as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe("https://tiktok.com/@huy.codes/video/v1");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
  });

  it("renders card without tiktok_url as a plain div (no link)", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: {
        niche_id: 7,
        hook_type: null,
        references: [makeRef({ tiktok_url: null })],
      },
      isPending: false,
    });
    renderStrip();
    expect(screen.queryByRole("link")).toBeNull();
    // Other content still renders.
    expect(screen.getByText("@huy.codes")).toBeTruthy();
  });

  it("hides duration chip when duration_sec is null", () => {
    mockUseIdeaReferences.mockReturnValue({
      data: {
        niche_id: 7,
        hook_type: null,
        references: [makeRef({ duration_sec: null })],
      },
      isPending: false,
    });
    renderStrip();
    // Match% pill still present.
    expect(screen.getByText("96%")).toBeTruthy();
    // No duration text like "32s".
    expect(screen.queryByText(/^\d+s$/)).toBeNull();
  });
});
