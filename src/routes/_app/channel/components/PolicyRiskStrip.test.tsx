import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { PolicyRiskStrip } from "./PolicyRiskStrip";

afterEach(() => {
  cleanup();
});

describe("PolicyRiskStrip", () => {
  it("renders policy findings only", () => {
    render(
      <PolicyRiskStrip
        findings={[
          {
            finding_id: "channel_compliance_aggregate",
            teaser: "2/5 video có dấu hiệu compliance.",
            strength: "high",
          },
          {
            finding_id: "channel_view_ceiling_300",
            teaser: "Trần view.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText("2/5 video có dấu hiệu compliance.")).toBeTruthy();
    expect(screen.queryByText("Trần view.")).toBeNull();
  });

  it("returns null when no policy findings", () => {
    const { container } = render(
      <PolicyRiskStrip
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
