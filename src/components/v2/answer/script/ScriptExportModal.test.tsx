/**
 * ScriptExportModal tests — S4 (per design pack ``screens/script.jsx``
 * lines 838-927).
 *
 * Surface contracts:
 *   1. Hidden when ``open=false``.
 *   2. Renders three format radio cards with default ``shoot`` selected.
 *   3. Click radio updates selection (selected card carries aria-pressed).
 *   4. CTA submits the chosen format via ``onExport``.
 *   5. Cancel paths: X button, click-outside, Escape key.
 *   6. ``exported=true`` flips the CTA to ``Đã tải``; ``busy=true``
 *      disables the CTA.
 */

import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ScriptExportModal } from "./ScriptExportModal";

afterEach(cleanup);

describe("ScriptExportModal", () => {
  it("renders nothing when open=false", () => {
    const { container } = render(
      <ScriptExportModal
        open={false}
        onClose={vi.fn()}
        onExport={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders three format options with shoot selected by default", () => {
    render(
      <ScriptExportModal open onClose={vi.fn()} onExport={vi.fn()} />,
    );
    expect(screen.getByText("Format quay")).toBeTruthy();
    expect(screen.getByText("Markdown")).toBeTruthy();
    expect(screen.getByText("Văn bản")).toBeTruthy();
    const shootBtn = screen.getByRole("button", { name: /Format quay/ });
    expect(shootBtn.getAttribute("aria-pressed")).toBe("true");
  });

  it("clicking a format updates aria-pressed selection", () => {
    render(
      <ScriptExportModal open onClose={vi.fn()} onExport={vi.fn()} />,
    );
    const mdBtn = screen.getByRole("button", { name: /Markdown/ });
    fireEvent.click(mdBtn);
    expect(mdBtn.getAttribute("aria-pressed")).toBe("true");
    const shootBtn = screen.getByRole("button", { name: /Format quay/ });
    expect(shootBtn.getAttribute("aria-pressed")).toBe("false");
  });

  it("CTA submits the currently-selected format", () => {
    const onExport = vi.fn();
    render(<ScriptExportModal open onClose={vi.fn()} onExport={onExport} />);
    fireEvent.click(screen.getByRole("button", { name: /Markdown/ }));
    fireEvent.click(screen.getByRole("button", { name: /Tải file/ }));
    expect(onExport).toHaveBeenCalledTimes(1);
    expect(onExport).toHaveBeenCalledWith("markdown");
  });

  it("X button calls onClose", () => {
    const onClose = vi.fn();
    render(<ScriptExportModal open onClose={onClose} onExport={vi.fn()} />);
    fireEvent.click(screen.getByLabelText(/Đóng/));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("Hủy button calls onClose", () => {
    const onClose = vi.fn();
    render(<ScriptExportModal open onClose={onClose} onExport={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /^Hủy$/ }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("clicking the overlay calls onClose; clicking the dialog body does NOT", () => {
    const onClose = vi.fn();
    const { container } = render(
      <ScriptExportModal open onClose={onClose} onExport={vi.fn()} />,
    );
    const overlay = container.querySelector('[role="dialog"]') as HTMLElement;
    expect(overlay).toBeTruthy();
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalledTimes(1);
    // Click inside the dialog body should not bubble up to onClose again.
    fireEvent.click(screen.getByText("Chọn định dạng"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("Escape key calls onClose", () => {
    const onClose = vi.fn();
    render(<ScriptExportModal open onClose={onClose} onExport={vi.fn()} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('exported=true flips the CTA to "Đã tải"', () => {
    render(
      <ScriptExportModal open exported onClose={vi.fn()} onExport={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: /Đã tải/ })).toBeTruthy();
  });

  it("busy=true disables the CTA", () => {
    render(
      <ScriptExportModal open busy onClose={vi.fn()} onExport={vi.fn()} />,
    );
    const cta = screen.getByRole("button", { name: /Đang xuất/ }) as HTMLButtonElement;
    expect(cta.disabled).toBe(true);
  });
});
