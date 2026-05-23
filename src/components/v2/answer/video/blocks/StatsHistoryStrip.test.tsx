import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatsHistoryStrip } from "./StatsHistoryStrip";

describe("StatsHistoryStrip", () => {
  it("renders nothing when fewer than 2 snapshots", () => {
    const { container } = render(
      <StatsHistoryStrip history={[{ at: "x", phase: "t0", views: 100, likes: 1, comments: 0, shares: 0 }]} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders phase rows and spike_then_flat badge", () => {
    render(
      <StatsHistoryStrip
        distributionShape="spike_then_flat"
        history={[
          { at: "a", phase: "t0", views: 1000, likes: 50, comments: 10, shares: 5 },
          { at: "b", phase: "t6h", views: 5000, likes: 80, comments: 12, shares: 4 },
        ]}
      />,
    );
    expect(screen.getByText(/Spike rồi phẳng/)).toBeTruthy();
    expect(screen.getByText("1.0K")).toBeTruthy();
    expect(screen.getByText("5.0K")).toBeTruthy();
  });
});
