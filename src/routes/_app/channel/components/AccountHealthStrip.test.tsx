import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AccountHealthStrip } from "./AccountHealthStrip";

afterEach(() => {
  cleanup();
});

describe("AccountHealthStrip", () => {
  it("renders account health findings only", () => {
    render(
      <AccountHealthStrip
        findings={[
          {
            finding_id: "channel_view_ceiling_300",
            teaser: "Có dấu hiệu trần view.",
            strength: "high",
          },
          {
            finding_id: "channel_compliance_aggregate",
            teaser: "Compliance flag.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText("Có dấu hiệu trần view.")).toBeTruthy();
    expect(screen.queryByText("Compliance flag.")).toBeNull();
    expect(screen.getByText(/Account Status/)).toBeTruthy();
  });

  it("returns null when no account health findings", () => {
    const { container } = render(
      <AccountHealthStrip
        findings={[
          {
            finding_id: "channel_format_entropy_high",
            teaser: "Format phân tán.",
            strength: "medium",
          },
        ]}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
