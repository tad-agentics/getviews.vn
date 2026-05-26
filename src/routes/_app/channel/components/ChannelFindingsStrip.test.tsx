import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChannelAuditRingsPanel } from "./ChannelAuditRingsPanel";
import { ChannelFindingsStrip } from "./ChannelFindingsStrip";

afterEach(() => {
  cleanup();
});

describe("ChannelAuditRingsPanel", () => {
  it("renders all five audit rings with clear state when no findings", () => {
    render(<ChannelAuditRingsPanel findings={[]} />);
    expect(screen.getByText(/Vòng 0 — Trước khi đăng/)).toBeTruthy();
    expect(screen.getByText(/Vòng 4 — Ngách & khán giả/)).toBeTruthy();
    expect(screen.getAllByText(/— chưa có tín hiệu/).length).toBe(5);
  });

  it("shows Vòng 1 alert with finding teaser and Account Status hint", () => {
    render(
      <ChannelAuditRingsPanel
        findings={[
          {
            finding_id: "channel_view_ceiling_300",
            teaser: "Có dấu hiệu trần view.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText(/⚠ cần xem/)).toBeTruthy();
    expect(screen.getByText("Có dấu hiệu trần view.")).toBeTruthy();
    expect(screen.getByText(/Account Status/)).toBeTruthy();
  });

  it("maps compliance findings to Vòng 0", () => {
    render(
      <ChannelAuditRingsPanel
        findings={[
          {
            finding_id: "channel_compliance_aggregate",
            teaser: "2/5 video có compliance flag.",
            strength: "high",
          },
        ]}
      />,
    );
    const v0 = screen.getByText(/Vòng 0 — Trước khi đăng/).closest("li");
    expect(v0?.textContent).toContain("2/5 video có compliance flag.");
  });

  it("maps format entropy to Vòng 2", () => {
    render(
      <ChannelAuditRingsPanel
        findings={[
          {
            finding_id: "channel_format_entropy_high",
            teaser: "Format phân tán.",
            strength: "medium",
          },
        ]}
      />,
    );
    const v2 = screen.getByText(/Vòng 2 — Mở rộng/).closest("li");
    expect(v2?.textContent).toContain("Format phân tán.");
  });

  it("maps peer saturation to Vòng 3", () => {
    render(
      <ChannelAuditRingsPanel
        findings={[
          {
            finding_id: "channel_peer_format_saturation",
            teaser: "Format bão hòa peer.",
            strength: "high",
          },
        ]}
      />,
    );
    const v3 = screen.getByText(/Vòng 3 — Xu hướng/).closest("li");
    expect(v3?.textContent).toContain("Format bão hòa peer.");
  });

  it("maps audience drop to Vòng 4", () => {
    render(
      <ChannelAuditRingsPanel
        findings={[
          {
            finding_id: "channel_recent_vs_peak_er_drop",
            teaser: "View gần đây thấp hơn peak.",
            strength: "medium",
          },
        ]}
      />,
    );
    const v4 = screen.getByText(/Vòng 4 — Ngách & khán giả/).closest("li");
    expect(v4?.textContent).toContain("View gần đây thấp hơn peak.");
  });
});

describe("ChannelFindingsStrip", () => {
  it("delegates to ChannelAuditRingsPanel", () => {
    render(
      <ChannelFindingsStrip
        findings={[
          {
            finding_id: "channel_format_entropy_high",
            teaser: "Format kênh phân tán.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Kiểm toán theo Vòng/)).toBeTruthy();
    expect(screen.getByText("Format kênh phân tán.")).toBeTruthy();
  });
});
