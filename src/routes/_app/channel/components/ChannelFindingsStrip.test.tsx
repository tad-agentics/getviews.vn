import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChannelFindingsStrip } from "./ChannelFindingsStrip";

afterEach(() => {
  cleanup();
});

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

  it("shows Vòng 2 hint for format entropy finding", () => {
    render(
      <ChannelFindingsStrip
        findings={[
          {
            finding_id: "channel_format_entropy_high",
            teaser: "Format phân tán.",
            strength: "medium",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Vòng 2 \(format & persona\)/)).toBeTruthy();
  });

  it("shows Vòng 3 hint for compliance finding without duplicating teaser in strip", () => {
    render(
      <ChannelFindingsStrip
        findings={[
          {
            finding_id: "channel_compliance_aggregate",
            teaser: "2/5 video có compliance flag.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Vòng 3 \(compliance\)/)).toBeTruthy();
    expect(screen.queryByText("2/5 video có compliance flag.")).toBeNull();
  });

  it("shows Vòng 4 hint for audience mismatch finding", () => {
    render(
      <ChannelFindingsStrip
        findings={[
          {
            finding_id: "channel_recent_vs_peak_er_drop",
            teaser: "View gần đây thấp hơn peak.",
            strength: "medium",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Vòng 4 \(audience & ngách\)/)).toBeTruthy();
    expect(screen.getByText("View gần đây thấp hơn peak.")).toBeTruthy();
  });
});
