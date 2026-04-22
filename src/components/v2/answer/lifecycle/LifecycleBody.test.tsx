/**
 * LifecycleBody — render + mode-driven copy regression.
 *
 * The backend ships three modes (``format`` / ``hook_fatigue`` /
 * ``subniche``) that all use the same payload shape but expect
 * different supplementary cell fields. These tests pin the "which
 * field surfaces in which mode" contract so a schema drift can't
 * silently mis-render.
 */
import React from "react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
  },
}));

import type {
  LifecycleCellData,
  LifecycleReportPayload,
  RefreshMoveData,
} from "@/lib/api-types";
import { LifecycleBody } from "./LifecycleBody";

afterEach(cleanup);

// ── Payload factories ─────────────────────────────────────────────────────

function mkCell(overrides: Partial<LifecycleCellData> = {}): LifecycleCellData {
  return {
    name: "Tutorial",
    stage: "rising",
    reach_delta_pct: 28,
    health_score: 82,
    retention_pct: null,
    instance_count: null,
    insight: "Insight stub",
    ...overrides,
  };
}

function mkReport(
  overrides: Partial<LifecycleReportPayload> = {},
): LifecycleReportPayload {
  return {
    confidence: {
      sample_size: 200,
      window_days: 30,
      niche_scope: "Skincare",
      freshness_hours: 3,
      intent_confidence: "high",
      what_stalled_reason: null,
    },
    mode: "format",
    subject_line: "Subject stub",
    cells: [mkCell()],
    refresh_moves: [],
    actions: [],
    sources: [],
    related_questions: [],
    ...overrides,
  };
}

function renderBody(report: LifecycleReportPayload) {
  return render(
    <MemoryRouter>
      <LifecycleBody report={report} />
    </MemoryRouter>,
  );
}

// ── Header copy driven by mode ────────────────────────────────────────────

describe("LifecycleBody mode header", () => {
  it("format mode shows 'Chu trình format' kicker", () => {
    renderBody(mkReport({ mode: "format" }));
    expect(screen.getByText("Chu trình format")).toBeTruthy();
  });

  it("hook_fatigue mode shows 'Hook fatigue' kicker", () => {
    renderBody(mkReport({ mode: "hook_fatigue" }));
    expect(screen.getByText("Hook fatigue")).toBeTruthy();
  });

  it("subniche mode shows 'Ngách con' kicker", () => {
    renderBody(mkReport({ mode: "subniche" }));
    expect(screen.getByText("Ngách con")).toBeTruthy();
  });
});

// ── Subject line render ───────────────────────────────────────────────────

describe("LifecycleBody subject line", () => {
  it("renders the subject_line text directly (no template prefix)", () => {
    renderBody(
      mkReport({ subject_line: "Tutorial đang lên +28% — chuyển 60% content." }),
    );
    expect(
      screen.getByText("Tutorial đang lên +28% — chuyển 60% content."),
    ).toBeTruthy();
  });
});

// ── Mode-specific supplementary fields ────────────────────────────────────

describe("LifecycleBody supplementary cell fields", () => {
  it("format mode surfaces retention_pct when present", () => {
    renderBody(
      mkReport({
        mode: "format",
        cells: [mkCell({ retention_pct: 73 })],
      }),
    );
    expect(screen.getByText(/Retention 73%/)).toBeTruthy();
  });

  it("format mode omits retention row when retention_pct is null", () => {
    renderBody(
      mkReport({
        mode: "format",
        cells: [mkCell({ retention_pct: null })],
      }),
    );
    expect(screen.queryByText(/Retention/)).toBeNull();
  });

  it("subniche mode surfaces instance_count with VN locale formatting", () => {
    renderBody(
      mkReport({
        mode: "subniche",
        cells: [mkCell({ instance_count: 1240 })],
      }),
    );
    // Vietnamese locale groups thousands with "." — assert on the number
    // substring instead of a full match to avoid locale-runtime drift.
    expect(screen.getByText(/1\.240 creator đang làm/)).toBeTruthy();
  });

  it("hook_fatigue mode never shows retention_pct nor instance_count", () => {
    renderBody(
      mkReport({
        mode: "hook_fatigue",
        cells: [mkCell({ retention_pct: 73, instance_count: 540 })],
      }),
    );
    // Even when present in data, hook_fatigue mode ignores them.
    expect(screen.queryByText(/Retention/)).toBeNull();
    expect(screen.queryByText(/creator đang làm/)).toBeNull();
  });
});

// ── Cell stage pill tones ─────────────────────────────────────────────────

describe("LifecycleBody stage pills", () => {
  it("renders Vietnamese stage labels, not the raw enum", () => {
    renderBody(
      mkReport({
        cells: [
          mkCell({ stage: "rising" }),
          mkCell({ stage: "peak", name: "Peak cell" }),
          mkCell({ stage: "plateau", name: "Plateau cell" }),
          mkCell({ stage: "declining", name: "Declining cell" }),
        ],
      }),
    );
    expect(screen.getByText("Đang lên")).toBeTruthy();
    expect(screen.getByText("Đỉnh")).toBeTruthy();
    expect(screen.getByText("Chững")).toBeTruthy();
    expect(screen.getByText("Giảm")).toBeTruthy();
    // Raw enum labels must not leak into the UI.
    expect(screen.queryByText("rising")).toBeNull();
    expect(screen.queryByText("declining")).toBeNull();
  });
});

// ── Delta formatting ──────────────────────────────────────────────────────

describe("LifecycleBody delta formatting", () => {
  it("prefixes positive delta with '+'", () => {
    renderBody(mkReport({ cells: [mkCell({ reach_delta_pct: 28 })] }));
    expect(screen.getByText("+28%")).toBeTruthy();
  });

  it("keeps negative delta without a + prefix", () => {
    renderBody(
      mkReport({ cells: [mkCell({ reach_delta_pct: -18, stage: "declining" })] }),
    );
    expect(screen.getByText("-18%")).toBeTruthy();
  });
});

// ── Refresh moves ─────────────────────────────────────────────────────────

describe("LifecycleBody refresh moves", () => {
  it("does not render the refresh section when moves is empty", () => {
    renderBody(mkReport({ refresh_moves: [] }));
    expect(screen.queryByText("Refresh")).toBeNull();
    expect(screen.queryByText(/Cách làm mới cell đang yếu/)).toBeNull();
  });

  it("renders each refresh move with effort label when moves are present", () => {
    const moves: RefreshMoveData[] = [
      { title: "Đổi audio", detail: "Detail A", effort: "low" },
      { title: "Rút hook", detail: "Detail B", effort: "medium" },
    ];
    renderBody(
      mkReport({
        cells: [mkCell({ stage: "declining", reach_delta_pct: -10 })],
        refresh_moves: moves,
      }),
    );
    expect(screen.getByText("Đổi audio")).toBeTruthy();
    expect(screen.getByText("Rút hook")).toBeTruthy();
    expect(screen.getByText("Công sức thấp")).toBeTruthy();
    expect(screen.getByText("Công sức vừa")).toBeTruthy();
  });
});

// ── Thin-corpus MẪU MỎNG toggle ───────────────────────────────────────────

describe("LifecycleBody thin-sample humility banner", () => {
  it("shows 'MẪU MỎNG' chip when sample_size < 80", () => {
    renderBody(
      mkReport({
        confidence: {
          sample_size: 42,
          window_days: 30,
          niche_scope: "Skincare",
          freshness_hours: 8,
          intent_confidence: "low",
          what_stalled_reason: null,
        },
      }),
    );
    expect(screen.getByText("MẪU MỎNG")).toBeTruthy();
  });

  it("hides the chip when sample_size >= 80", () => {
    renderBody(
      mkReport({
        confidence: {
          sample_size: 200,
          window_days: 30,
          niche_scope: "Skincare",
          freshness_hours: 3,
          intent_confidence: "high",
          what_stalled_reason: null,
        },
      }),
    );
    expect(screen.queryByText("MẪU MỎNG")).toBeNull();
  });
});

// ── Actions section ───────────────────────────────────────────────────────

describe("LifecycleBody action cards", () => {
  it("hides the actions section entirely when actions is empty", () => {
    renderBody(mkReport({ actions: [] }));
    expect(screen.queryByText("Bước tiếp theo")).toBeNull();
  });

  it("renders action cards header when actions are present", () => {
    renderBody(
      mkReport({
        actions: [
          {
            icon: "sparkles",
            title: "Test action",
            sub: "Stub sub",
            cta: "Mở",
            primary: true,
            route: "/app/script",
            forecast: { expected_range: "+28%", baseline: "1.0×" },
          },
        ],
      }),
    );
    expect(screen.getByText("Bước tiếp theo")).toBeTruthy();
    expect(screen.getByText("Test action")).toBeTruthy();
  });
});
