/**
 * BUG-free guard: the content-calendar strip added 2026-04-22 must stay
 * hidden on pure timing queries and render all 4 kind variants when
 * populated. Protects the invariants from
 * ``artifacts/docs/report-template-prd-timing-calendar.md``.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CalendarSlotData, CalendarSlotKindData } from "@/lib/api-types";

import { CalendarStrip } from "./CalendarStrip";

function slot(overrides: Partial<CalendarSlotData> = {}): CalendarSlotData {
  return {
    day_idx: 2,
    day: "Thứ 4",
    suggested_time: "20:00",
    kind: "pattern",
    title: "Hook cảm xúc mới",
    rationale: "Khung Thứ 4 20:00 đang dẫn đầu ngách Skincare — gấp 1.8× trung bình.",
    ...overrides,
  };
}

describe("CalendarStrip", () => {
  it("renders nothing when slots is empty — pure timing query stays heatmap-only", () => {
    const { container } = render(<CalendarStrip slots={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the section heading when slots are present", () => {
    render(<CalendarStrip slots={[slot()]} />);
    expect(screen.getByText(/Lịch content tuần/i)).toBeTruthy();
  });

  it("renders exactly 7 day cells (Mon–Sun) regardless of how many slots", () => {
    const { container } = render(<CalendarStrip slots={[slot({ day_idx: 2 })]} />);
    const grid = container.querySelector(".grid");
    expect(grid).toBeTruthy();
    expect(grid!.children.length).toBe(7);
  });

  it("renders 6 empty-cell placeholders when only one slot is filled", () => {
    const { container } = render(<CalendarStrip slots={[slot({ day_idx: 2 })]} />);
    // Empty cells carry aria-label ending with "không có đề xuất".
    const empties = container.querySelectorAll('[aria-label$="không có đề xuất"]');
    expect(empties.length).toBe(6);
  });

  it.each<[CalendarSlotKindData, string]>([
    ["pattern", "Pattern"],
    ["ideas", "Ý tưởng"],
    ["timing", "Thời điểm"],
    ["repost", "Repost"],
  ])("renders the %s kind chip with its Vietnamese label", (kind, label) => {
    const { container } = render(<CalendarStrip slots={[slot({ kind })]} />);
    // Scope to the kind-chip span only — the section heading also
    // contains "content" etc. so a bare getByText can match multiple
    // nodes depending on kind label wording.
    const chips = Array.from(container.querySelectorAll("span.inline-flex"))
      .map((n) => n.textContent?.trim() ?? "");
    expect(chips).toContain(label);
  });

  it("renders Mon→Sun when slots come in out of order", () => {
    const slots: CalendarSlotData[] = [
      slot({ day_idx: 5, day: "Thứ 7", title: "Weekend repost", kind: "repost" }),
      slot({ day_idx: 0, day: "Thứ 2", title: "Monday pattern", kind: "pattern" }),
      slot({ day_idx: 3, day: "Thứ 5", title: "Thursday ideas", kind: "ideas" }),
    ];
    const { container } = render(<CalendarStrip slots={slots} />);
    const grid = container.querySelector(".grid");
    const labels = Array.from(grid!.querySelectorAll("span.gv-mono"))
      .map((n) => n.textContent?.trim() ?? "")
      .filter((t) => /^(Thứ|CN)/.test(t));
    expect(labels).toEqual(["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]);
  });

  it("shows the slot's suggested time", () => {
    render(<CalendarStrip slots={[slot({ suggested_time: "18:30" })]} />);
    expect(screen.getByText("18:30")).toBeTruthy();
  });

  it("exposes the rationale as a title attribute for hover", () => {
    const { container } = render(
      <CalendarStrip slots={[slot({ rationale: "Khung A · gấp 2.5× ngách" })]} />,
    );
    const cell = container.querySelector('[title="Khung A · gấp 2.5× ngách"]');
    expect(cell).toBeTruthy();
  });
});
