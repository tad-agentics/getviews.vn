import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { LivePipelineStrip } from "./ResearchStrip";

describe("LivePipelineStrip", () => {
  it("renders nothing when idle with no step events (error / pre-stream)", () => {
    const { container } = render(
      <LivePipelineStrip steps={[]} done={false} loading={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when done with no step events", () => {
    const { container } = render(
      <LivePipelineStrip steps={[]} done={true} loading={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the 4-stage process bar while loading with no step events yet", () => {
    render(<LivePipelineStrip steps={[]} done={false} loading={true} />);
    expect(screen.getByLabelText("Tiến trình nghiên cứu")).toBeTruthy();
  });
});
