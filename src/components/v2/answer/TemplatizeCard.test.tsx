import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { TemplatizeCard } from "./TemplatizeCard";

describe("TemplatizeCard", () => {
  it("exposes visible accessible names for both actions", () => {
    render(<TemplatizeCard sessionId="sess-1" />);
    expect(screen.getByRole("button", { name: "Lưu" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Chia sẻ" })).toBeTruthy();
  });
});
