import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChannelFindingsStrip } from "./ChannelFindingsStrip";

describe("ChannelFindingsStrip", () => {
  it("renders finding teasers with strength label", () => {
    render(
      <ChannelFindingsStrip
        findings={[
          {
            finding_id: "channel_view_ceiling_300",
            teaser: "Có dấu hiệu trần view quanh 300.",
            strength: "high",
          },
        ]}
      />,
    );
    expect(screen.getByText("Mạnh")).toBeTruthy();
    expect(screen.getByText("Có dấu hiệu trần view quanh 300.")).toBeTruthy();
  });

  it("returns null when findings empty", () => {
    const { container } = render(<ChannelFindingsStrip findings={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
