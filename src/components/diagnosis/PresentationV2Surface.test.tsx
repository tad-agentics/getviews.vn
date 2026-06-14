import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ExpandableList } from "./ExpandableList";
import { RetentionCurveChart } from "./RetentionCurveChart";

vi.mock("@/lib/presentationV2", () => ({
  isReportPresentationV2: () => true,
}));

afterEach(cleanup);

describe("RetentionCurveChart", () => {
  it("renders legend and hides when user curve empty", () => {
    const empty = render(
      <RetentionCurveChart userCurve={[]} durationSec={30} />,
    );
    expect(empty.container.firstChild).toBeNull();

    const { container } = render(
      <RetentionCurveChart
        userCurve={[
          { t: 0, pct: 100 },
          { t: 3, pct: 72 },
        ]}
        nicheCurve={[{ t: 0, pct: 100 }, { t: 3, pct: 80 }]}
        durationSec={15}
        riskEvents={[{ t: 3, reason_vi: "Rớt mạnh sau chuyển cảnh" }]}
      />,
    );
    expect(container.textContent).toMatch(/Đường liền = giữ chân/);
    expect(container.textContent).toMatch(/Rớt mạnh nhất: 3\.0s — Rớt mạnh/);
  });
});

describe("ExpandableList", () => {
  it("shows Xem thêm affordance when list exceeds cap", () => {
    render(
      <ExpandableList
        items={["a", "b", "c", "d"]}
        initialCount={2}
        renderItem={(item) => <span>{item}</span>}
        itemKey={(item) => item}
      />,
    );
    expect(screen.getByText("a")).toBeTruthy();
    expect(screen.getByText("b")).toBeTruthy();
    expect(screen.queryByText("c")).toBeNull();
    const trigger = screen.getByRole("button", { name: /Xem thêm \(2\)/i });
    expect(trigger).toBeTruthy();

    fireEvent.click(trigger);
    expect(screen.getByRole("button", { name: /Thu gọn/i })).toBeTruthy();
  });
});
