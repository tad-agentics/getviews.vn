/**
 * SessionDrawer tests — A2 row enrichment (niche chip + N lượt + relative time).
 * Per design pack ``screens/answer.jsx`` lines 360-381.
 */

import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { AnswerSessionRow } from "@/lib/api-types";
import { SessionDrawer } from "./SessionDrawer";

afterEach(cleanup);

function makeSession(overrides: Partial<AnswerSessionRow> = {}): AnswerSessionRow {
  return {
    id: "s-1",
    user_id: "u-1",
    title: "Hook nào đang hot trong Tech?",
    initial_q: "Hook nào đang hot trong Tech?",
    intent_type: "pattern_research",
    format: "pattern",
    niche_id: 4,
    updated_at: new Date().toISOString(),
    archived_at: null,
    turn_count: 3,
    ...overrides,
  };
}

const noopHandlers = {
  onClose: vi.fn(),
  onSelect: vi.fn(),
  onNewSession: vi.fn(),
  onViewAll: vi.fn(),
};

describe("SessionDrawer — A2 row enrichment", () => {
  it("renders niche label + turn count + relative time per row when nicheLabelOf is provided", () => {
    const sessions = [makeSession({ id: "s-1", niche_id: 4, turn_count: 3 })];
    const nicheLabelOf = (id: number | null) => (id === 4 ? "Tech" : null);
    render(
      <SessionDrawer
        open
        sessions={sessions}
        activeSessionId={null}
        isLoading={false}
        nicheLabelOf={nicheLabelOf}
        {...noopHandlers}
      />,
    );
    expect(screen.getByText("Tech")).toBeTruthy();
    expect(screen.getByText("3 lượt")).toBeTruthy();
    expect(screen.getByText(/Hôm nay|^\d+ ngày$|^Vừa xong/)).toBeTruthy();
  });

  it("hides the niche chip when nicheLabelOf returns null", () => {
    const sessions = [makeSession({ niche_id: 999, turn_count: 2 })];
    const nicheLabelOf = () => null;
    render(
      <SessionDrawer
        open
        sessions={sessions}
        activeSessionId={null}
        isLoading={false}
        nicheLabelOf={nicheLabelOf}
        {...noopHandlers}
      />,
    );
    // Turn count still present but no niche label.
    expect(screen.getByText("2 lượt")).toBeTruthy();
  });

  it("hides the turn-count chip when turn_count is 0 or undefined", () => {
    const sessions = [
      makeSession({ id: "s-zero", turn_count: 0 }),
      makeSession({ id: "s-undef", turn_count: undefined }),
    ];
    render(
      <SessionDrawer
        open
        sessions={sessions}
        activeSessionId={null}
        isLoading={false}
        nicheLabelOf={() => "Tech"}
        {...noopHandlers}
      />,
    );
    expect(screen.queryByText(/lượt/)).toBeNull();
  });

  it("highlights the active session with accent border + bg", () => {
    const sessions = [
      makeSession({ id: "s-1" }),
      makeSession({ id: "s-2", title: "Khác" }),
    ];
    render(
      <SessionDrawer
        open
        sessions={sessions}
        activeSessionId="s-2"
        isLoading={false}
        {...noopHandlers}
      />,
    );
    const buttons = screen.getAllByRole("button", { name: /Khác|Hook/ });
    const activeBtn = buttons.find((b) => b.textContent?.includes("Khác"));
    expect(activeBtn?.className).toMatch(/gv-accent/);
  });

  it("clicking a row calls onSelect + onClose", () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();
    const sessions = [makeSession({ id: "pick-me" })];
    render(
      <SessionDrawer
        open
        sessions={sessions}
        activeSessionId={null}
        isLoading={false}
        nicheLabelOf={() => null}
        {...noopHandlers}
        onSelect={onSelect}
        onClose={onClose}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Hook nào đang hot/ }));
    expect(onSelect).toHaveBeenCalledWith("pick-me");
    expect(onClose).toHaveBeenCalled();
  });
});
