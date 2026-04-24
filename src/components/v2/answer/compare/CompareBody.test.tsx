/**
 * Wave 4 PR #3 — CompareBody coverage.
 *
 * Pins:
 * - delta verdict + numeric chips render from a well-formed payload
 * - sticky A/B side labels appear on each panel header
 * - per-side stats (Views / Breakout / Scene / Hook) all surface, with
 *   the "—" fallback when a metric is missing
 * - verdict_fallback flag surfaces the muted "(tổng hợp tự động)" line
 * - missing breakout_gap or scene_count_diff doesn't crash; chips just
 *   don't render
 */
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
  },
}));

import type {
  CompareDelta,
  ComparePayload,
  VideoDiagnosisStreamSide,
} from "@/lib/api-types";
import { CompareBody } from "./CompareBody";

afterEach(cleanup);

function mkSide(overrides: Partial<VideoDiagnosisStreamSide> = {}): VideoDiagnosisStreamSide {
  return {
    intent: "video_diagnosis",
    niche: "skincare",
    metadata: {
      video_id: "v1",
      duration_sec: 30,
      engagement_rate: 4.5,
      breakout: 1.5,
      metrics: { views: 100_000, likes: 5_000, comments: 200, shares: 100 },
      author: { username: "creator_a" },
    },
    analysis: {
      transitions_per_second: 0.4,
      scenes: [{ i: 0 }, { i: 1 }, { i: 2 }, { i: 3 }, { i: 4 }],
      hook_analysis: { hook_type: "question" },
    },
    diagnosis: "Video chạy tốt - hook mạnh, pacing chuẩn.",
    ...overrides,
  };
}

function mkDelta(overrides: Partial<CompareDelta> = {}): CompareDelta {
  return {
    verdict: "Video trái mạnh hơn 1.5x — cùng hook nhưng pacing khác.",
    hook_alignment: "match",
    higher_breakout_side: "left",
    breakout_gap: 0.5,
    scene_count_diff: 2,
    transitions_per_second_diff: 0.1,
    left_hook_type: "question",
    right_hook_type: "question",
    verdict_fallback: false,
    ...overrides,
  };
}

function mkPayload(overrides: Partial<ComparePayload> = {}): ComparePayload {
  return {
    intent: "compare_videos",
    niche: "skincare",
    left: mkSide({ metadata: { ...mkSide().metadata, author: { username: "left_creator" } } }),
    right: mkSide({
      metadata: { ...mkSide().metadata, author: { username: "right_creator" }, breakout: 1.0 },
    }),
    delta: mkDelta(),
    ...overrides,
  };
}

// ── Delta bar ────────────────────────────────────────────────────────

describe("CompareBody — delta bar", () => {
  it("renders the verdict sentence verbatim", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ verdict: "Hook khác kiểu — pacing chậm hơn ở video phải." }),
    })} />);
    expect(
      screen.getByText("Hook khác kiểu — pacing chậm hơn ở video phải."),
    ).toBeTruthy();
  });

  it("emits the KHÁC BIỆT CHÍNH kicker", () => {
    render(<CompareBody payload={mkPayload()} />);
    // Match case-insensitive — the kicker uses gv-uc class which
    // visually uppercases but the DOM text stays "Khác biệt chính".
    expect(screen.getByText(/Khác biệt chính/i)).toBeTruthy();
  });

  it("shows the higher-side chip in Vietnamese", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ higher_breakout_side: "right" }),
    })} />);
    expect(screen.getByText("Video phải mạnh hơn")).toBeTruthy();
  });

  it("shows the hook-alignment chip in Vietnamese", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ hook_alignment: "conflict" }),
    })} />);
    expect(screen.getByText("Hook khác kiểu")).toBeTruthy();
  });

  it("renders breakout-gap chip with sign + 2 decimals", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ breakout_gap: 0.74 }),
    })} />);
    expect(screen.getByText(/\+0\.74x/)).toBeTruthy();
  });

  it("hides breakout-gap chip when gap is null", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ breakout_gap: null, higher_breakout_side: "unknown" }),
    })} />);
    // No "Δ breakout" text anywhere when the metric is missing.
    expect(screen.queryByText(/Δ breakout/i)).toBeNull();
  });

  it("shows scene-count-diff chip with sign", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ scene_count_diff: -3 }),
    })} />);
    expect(screen.getByText(/Δ scene -3/)).toBeTruthy();
  });

  it("hides scene-count-diff chip when null", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ scene_count_diff: null }),
    })} />);
    expect(screen.queryByText(/Δ scene/i)).toBeNull();
  });

  it("surfaces verdict_fallback notice when flag is true", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ verdict_fallback: true }),
    })} />);
    expect(screen.getByTestId("compare-delta-fallback")).toBeTruthy();
  });

  it("hides verdict_fallback notice on Gemini-success path", () => {
    render(<CompareBody payload={mkPayload({
      delta: mkDelta({ verdict_fallback: false }),
    })} />);
    expect(screen.queryByTestId("compare-delta-fallback")).toBeNull();
  });
});

// ── Side panels ──────────────────────────────────────────────────────

describe("CompareBody — side panels", () => {
  it("emits A and B labels on the two side headers", () => {
    render(<CompareBody payload={mkPayload()} />);
    expect(screen.getByLabelText("Video A")).toBeTruthy();
    expect(screen.getByLabelText("Video B")).toBeTruthy();
  });

  it("renders both creator handles without double @", () => {
    render(<CompareBody payload={mkPayload()} />);
    // mkPayload sets handles to left_creator / right_creator.
    expect(screen.getByText("@left_creator")).toBeTruthy();
    expect(screen.getByText("@right_creator")).toBeTruthy();
  });

  it("formats views in vi-VN locale (1.234 grouping)", () => {
    render(<CompareBody payload={mkPayload({
      left: mkSide({
        metadata: {
          ...mkSide().metadata,
          metrics: { views: 1_234_567 },
          author: { username: "x" },
        },
      }),
    })} />);
    // vi-VN groups with "." → "1.234.567"
    expect(screen.getByText("1.234.567")).toBeTruthy();
  });

  it("renders breakout with 2-decimal x suffix", () => {
    render(<CompareBody payload={mkPayload({
      left: mkSide({
        metadata: { ...mkSide().metadata, breakout: 2.347, author: { username: "x" } },
      }),
    })} />);
    expect(screen.getByText("2.35x")).toBeTruthy();
  });

  it("falls back to — when a metric is missing", () => {
    render(<CompareBody payload={mkPayload({
      left: mkSide({
        metadata: {
          ...mkSide().metadata,
          metrics: { views: null },
          breakout: null,
          author: { username: "x" },
        },
        analysis: { ...mkSide().analysis, scenes: [], hook_analysis: { hook_type: null } },
      }),
    })} />);
    // 4 chips × side; at least the four "—" placeholders show.
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });

  it("renders the diagnosis prose for each side", () => {
    render(<CompareBody payload={mkPayload({
      left: mkSide({ diagnosis: "Lefts diagnosis VI." }),
      right: mkSide({ diagnosis: "Rights diagnosis VI." }),
    })} />);
    expect(screen.getByText("Lefts diagnosis VI.")).toBeTruthy();
    expect(screen.getByText("Rights diagnosis VI.")).toBeTruthy();
  });

  it("hides the diagnosis prose block when empty", () => {
    const { container } = render(<CompareBody payload={mkPayload({
      left: mkSide({ diagnosis: "" }),
      right: mkSide({ diagnosis: "" }),
    })} />);
    // No serif prose blocks for the diagnosis text — the chip grid
    // is the only content left under each header.
    const serifBlocks = container.querySelectorAll(".gv-serif.whitespace-pre-line");
    expect(serifBlocks.length).toBe(0);
  });
});

// ── Layout ───────────────────────────────────────────────────────────

describe("CompareBody — layout", () => {
  it("uses min-[900px]: two-column grid for the side panels", () => {
    const { container } = render(<CompareBody payload={mkPayload()} />);
    // The panel grid is the second top-level child after the delta bar.
    const grid = container.querySelector(".grid.grid-cols-1");
    expect(grid).toBeTruthy();
    expect(grid?.className).toContain("min-[900px]:grid-cols-2");
  });

  it("delta bar uses the brutalist surface class", () => {
    render(<CompareBody payload={mkPayload()} />);
    const bar = screen.getByTestId("compare-delta-bar");
    expect(bar.className).toContain("gv-surface-brutal");
  });
});
