/**
 * PR-6 Studio Home — FirstRunWelcomeStrip render-test.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FirstRunWelcomeStrip } from "./FirstRunWelcomeStrip";

afterEach(() => {
  cleanup();
});

describe("FirstRunWelcomeStrip", () => {
  it("renders the kicker, greeting with name + niche, and the hint sentence", () => {
    const { getByText } = render(
      <FirstRunWelcomeStrip
        firstName="An"
        nicheLabel="Công nghệ"
        onEditNiches={() => {}}
        onDismiss={() => {}}
      />,
    );
    expect(getByText(/NGÀY ĐẦU TIÊN/)).toBeTruthy();
    expect(getByText(/Chào An/)).toBeTruthy();
    expect(getByText("Công nghệ")).toBeTruthy();
    expect(getByText(/so sánh riêng/)).toBeTruthy();
  });

  it("invokes onEditNiches when the 'Đổi ngách / đối thủ' button is clicked", () => {
    const onEdit = vi.fn();
    const { getByText } = render(
      <FirstRunWelcomeStrip
        firstName="An"
        nicheLabel="Công nghệ"
        onEditNiches={onEdit}
        onDismiss={() => {}}
      />,
    );
    fireEvent.click(getByText(/Đổi ngách \/ đối thủ/));
    expect(onEdit).toHaveBeenCalledOnce();
  });

  it("invokes onDismiss when the close button is clicked", () => {
    const onDismiss = vi.fn();
    const { getByLabelText } = render(
      <FirstRunWelcomeStrip
        firstName="An"
        nicheLabel="Công nghệ"
        onEditNiches={() => {}}
        onDismiss={onDismiss}
      />,
    );
    fireEvent.click(getByLabelText("Đóng chào mừng"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("renders the strip with the ink fill + accent kicker tones", () => {
    const { container, getByText } = render(
      <FirstRunWelcomeStrip
        firstName="An"
        nicheLabel="Công nghệ"
        onEditNiches={() => {}}
        onDismiss={() => {}}
      />,
    );
    const section = container.querySelector("section");
    expect(section?.className).toMatch(/gv-ink/);
    expect(getByText(/NGÀY ĐẦU TIÊN/).className).toMatch(/gv-accent/);
  });
});
