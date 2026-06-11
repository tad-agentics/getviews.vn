import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ScriptNarrativeProse } from "./ScriptNarrativeProse";

describe("ScriptNarrativeProse", () => {
  it("links @handle tokens in prose", () => {
    render(
      <ScriptNarrativeProse text="Mirror cách @hi.vidayyy (27k view) mở hook." />,
    );
    const link = screen.getByRole("link", { name: "@hi.vidayyy" });
    expect(link.getAttribute("href")).toBe("https://www.tiktok.com/@hi.vidayyy");
  });
});
