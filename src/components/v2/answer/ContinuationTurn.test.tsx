/**
 * ContinuationTurn — payload.kind dispatch regression.
 *
 * This is the rendering half of the "no visible report" investigation: if
 * the SSE envelope's `payload.kind` doesn't match one of pattern / ideas /
 * timing / generic, the default branch must render `UnknownPayloadSurface`
 * (with the payload JSON visible) rather than silently emit nothing. An
 * earlier version of this file had no default case; turns with a malformed
 * or novel `kind` were rendered as a blank `<article>` and the user had no
 * signal that anything was wrong.
 */
import React from "react";
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

// Stub each report body with a signature component so the test asserts
// dispatch, not the full downstream render tree (which drags in niche-
// specific Supabase-shaped fixtures we don't need for this regression).
vi.mock("@/components/v2/answer/pattern/PatternBody", () => ({
  PatternBody: () => <div data-testid="pattern-body">pattern-body</div>,
}));
vi.mock("@/components/v2/answer/ideas/IdeasBody", () => ({
  IdeasBody: () => <div data-testid="ideas-body">ideas-body</div>,
}));
vi.mock("@/components/v2/answer/timing/TimingBody", () => ({
  TimingBody: () => <div data-testid="timing-body">timing-body</div>,
}));
vi.mock("@/components/v2/answer/lifecycle/LifecycleBody", () => ({
  LifecycleBody: () => <div data-testid="lifecycle-body">lifecycle-body</div>,
}));
vi.mock("@/components/v2/answer/diagnostic/DiagnosticBody", () => ({
  DiagnosticBody: () => <div data-testid="diagnostic-body">diagnostic-body</div>,
}));
vi.mock("@/components/v2/answer/generic/GenericBody", () => ({
  GenericBody: () => <div data-testid="generic-body">generic-body</div>,
}));

import { ContinuationTurn } from "./ContinuationTurn";
import type { AnswerTurnRow, ReportV1 } from "@/lib/api-types";

function mkTurn(payload: unknown, overrides: Partial<AnswerTurnRow> = {}): AnswerTurnRow {
  return {
    id: "turn-1",
    session_id: "sess-1",
    turn_index: 0,
    kind: "primary",
    query: "câu hỏi mẫu",
    payload: payload as ReportV1,
    ...overrides,
  };
}

afterEach(cleanup);

describe("ContinuationTurn payload dispatch", () => {
  // Kickers are Vietnamese per CLAUDE.md ("No English strings in UI").
  // If these strings are ever retranslated, update the `AnswerBlock`
  // call sites in ContinuationTurn.tsx in the same commit.
  //
  // Pattern is the one exception: ``ContinuationTurn.tsx:37`` wraps it
  // in ``<AnswerBlock kicker="Xu hướng" bare>``, and ``bare`` mode
  // intentionally drops the kicker chrome (``AnswerBlock.tsx:14-16``)
  // because PatternBody renders its own larger heading. So the Pattern
  // case asserts only the body — the other kicker assertions below
  // still apply to their non-bare AnswerBlocks.
  it("renders PatternBody for kind: pattern", () => {
    render(<ContinuationTurn turn={mkTurn({ kind: "pattern", report: {} })} />);
    expect(screen.getByTestId("pattern-body")).toBeTruthy();
  });

  it("renders IdeasBody inside a 'Ý tưởng' block for kind: ideas", () => {
    render(<ContinuationTurn turn={mkTurn({ kind: "ideas", report: {} })} />);
    expect(screen.getByTestId("ideas-body")).toBeTruthy();
    expect(screen.getByText("Ý tưởng")).toBeTruthy();
  });

  it("renders TimingBody inside a 'Thời điểm' block for kind: timing", () => {
    render(<ContinuationTurn turn={mkTurn({ kind: "timing", report: {} })} />);
    expect(screen.getByTestId("timing-body")).toBeTruthy();
    expect(screen.getByText("Thời điểm")).toBeTruthy();
  });

  it("renders LifecycleBody inside a 'Vòng đời' block for kind: lifecycle", () => {
    render(<ContinuationTurn turn={mkTurn({ kind: "lifecycle", report: {} })} />);
    expect(screen.getByTestId("lifecycle-body")).toBeTruthy();
    expect(screen.getByText("Vòng đời")).toBeTruthy();
  });

  it("renders DiagnosticBody inside a 'Chẩn đoán' block for kind: diagnostic", () => {
    render(<ContinuationTurn turn={mkTurn({ kind: "diagnostic", report: {} })} />);
    expect(screen.getByTestId("diagnostic-body")).toBeTruthy();
    expect(screen.getByText("Chẩn đoán")).toBeTruthy();
  });

  it("renders GenericBody with 'Tổng quát' kicker for kind: generic", () => {
    render(<ContinuationTurn turn={mkTurn({ kind: "generic", report: {} })} />);
    expect(screen.getByTestId("generic-body")).toBeTruthy();
    expect(screen.getByText("Tổng quát")).toBeTruthy();
  });

  it("renders UnknownPayloadSurface with payload JSON when kind is unrecognized", () => {
    // console.error is the diagnostic signal we explicitly want — silence it
    // from the test output so it doesn't look like a test failure.
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ContinuationTurn
        turn={mkTurn({ kind: "not_a_real_kind", report: { tldr: "meo" } })}
      />,
    );
    expect(screen.getByText("Báo cáo lỗi định dạng")).toBeTruthy();
    // Payload JSON should be embedded in the <pre> surface so the user can
    // copy-paste a diagnostic snapshot without opening devtools.
    expect(screen.getByText(/not_a_real_kind/)).toBeTruthy();
    expect(errSpy).toHaveBeenCalledWith(
      "[answer/turn] unknown payload.kind",
      expect.anything(),
    );
    errSpy.mockRestore();
  });

  it("renders UnknownPayloadSurface when `kind` is missing entirely", () => {
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<ContinuationTurn turn={mkTurn({ report: { x: 1 } })} />);
    expect(screen.getByText("Báo cáo lỗi định dạng")).toBeTruthy();
    // The pre shows the raw payload so team can diagnose what the server
    // actually emitted — key for investigating any future schema drift.
    expect(screen.getByText(/"report"/)).toBeTruthy();
    errSpy.mockRestore();
  });

  it("surfaces the turn_index + query header (follow-up turns labelled by kind)", () => {
    render(
      <ContinuationTurn
        turn={mkTurn(
          { kind: "timing", report: {} },
          { turn_index: 2, kind: "timing", query: "giờ nào tốt nhất?" },
        )}
      />,
    );
    // A1 — accent kicker is now "<KIND-LABEL> · LƯỢT NN" (zero-padded).
    // turn_index 2 → "LƯỢT 03"; kind=timing → "THỜI ĐIỂM".
    expect(screen.getByText(/THỜI ĐIỂM · LƯỢT 03/)).toBeTruthy();
    // Question is rendered as the polished serif H2.
    expect(screen.getByRole("heading", { level: 2, name: /giờ nào tốt nhất/ })).toBeTruthy();
    expect(screen.getByText(/giờ nào tốt nhất\?/)).toBeTruthy();
  });

  it("renders the per-turn MiniResearch ladder on first mount", () => {
    render(
      <ContinuationTurn
        turn={mkTurn(
          { kind: "ideas", report: {} },
          { turn_index: 1, kind: "ideas", query: "5 ý tưởng tuần này" },
        )}
      />,
    );
    // Both ladder steps rendered (animation runs on mount; we assert
    // structure, not the timed transitions).
    expect(screen.getByText(/Dùng lại nguồn/)).toBeTruthy();
    expect(screen.getByText(/Trả lời/)).toBeTruthy();
  });

  it("falls back to ĐÀO SÂU for unknown kinds", () => {
    render(
      <ContinuationTurn
        turn={mkTurn(
          { kind: "pattern", report: {} },
          { turn_index: 0, kind: "pattern", query: "đào sâu pattern" },
        )}
      />,
    );
    // ``pattern`` continuation turn maps to ĐÀO SÂU per the design.
    expect(screen.getByText(/ĐÀO SÂU · LƯỢT 01/)).toBeTruthy();
  });
});
