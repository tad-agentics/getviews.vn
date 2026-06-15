import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderInlineBold } from "./SectionProseBlocks";

describe("renderInlineBold", () => {
  it("renders guillemets and <<>> as strong", () => {
    render(
      <p>
        {renderInlineBold(
          "Với «Thiếu dấu hiệu tiêu cực — Giảm tin cậy», clip <<Get ready with me>> mạnh hơn.",
        )}
      </p>,
    );
    const gapTitle = screen.getByText("Thiếu dấu hiệu tiêu cực — Giảm tin cậy");
    expect(gapTitle.tagName).toBe("STRONG");
    expect(screen.getByText("Get ready with me", { selector: "strong" })).toBeTruthy();
  });

  it("skips empty emphasis pairs instead of rendering blank strong", () => {
    const { container } = render(
      <p>{renderInlineBold("Với ****: clip mạnh hơn.")}</p>,
    );
    const strongs = container.querySelectorAll("strong");
    for (const el of strongs) {
      expect(el.textContent?.trim()).not.toBe("");
    }
  });
});
