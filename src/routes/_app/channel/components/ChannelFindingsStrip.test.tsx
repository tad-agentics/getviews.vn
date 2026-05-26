import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChannelFindingsStrip } from "./ChannelFindingsStrip";

describe("ChannelFindingsStrip", () => {
  it("renders finding teasers with strength label", () => {
    render(
      <ChannelFindingsStrip
        findings={[
          {
            finding_id: "channel_format_entropy_high",
            teaser: "Format kênh phân tán — nhiều kiểu lẫn lộn.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText("Mạnh")).toBeTruthy();
    expect(screen.getByText("Format kênh phân tán — nhiều kiểu lẫn lộn.")).toBeTruthy();
    expect(screen.queryByText(/Vòng 1/)).toBeNull();
  });

  it("returns null when findings empty", () => {
    const { container } = render(<ChannelFindingsStrip findings={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows Vòng 1 hint when view ceiling finding present", () => {
    render(
      <ChannelFindingsStrip
        findings={[
          {
            finding_id: "channel_view_ceiling_300",
            teaser: "Có dấu hiệu trần view.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Vòng 1 \(sức khỏe tài khoản\)/)).toBeTruthy();
    expect(screen.getByText(/Account Status/)).toBeTruthy();
  });
});
