import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BoostAttributionBlock } from "./BoostAttributionBlock";

describe("BoostAttributionBlock", () => {
  it("renders nothing for organic_confident + eligible", () => {
    const { container } = render(
      <BoostAttributionBlock attribution="organic_confident" referenceEligible />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders suspect badge and ref-pool note", () => {
    render(
      <BoostAttributionBlock attribution="suspect_medium" referenceEligible={false} />,
    );
    expect(screen.getByLabelText("Phân loại nguồn lượt xem")).toBeTruthy();
    expect(screen.getByText(/Loại khỏi nhóm tham chiếu tự nhiên/)).toBeTruthy();
  });
});
