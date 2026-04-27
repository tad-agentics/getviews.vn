/**
 * ScriptExitModal tests — S4 (per design pack ``screens/script.jsx``
 * lines 800-835).
 *
 * Surface contracts:
 *   1. Hidden when ``open=false``.
 *   2. Renders kicker + H3 + body copy.
 *   3. Three actions wire to their respective callbacks.
 *   4. Click-outside and Escape both call onCancel.
 *   5. ``busy=true`` disables the save-and-exit CTA.
 */

import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ScriptExitModal } from "./ScriptExitModal";

afterEach(cleanup);

const noopHandlers = {
  onCancel: vi.fn(),
  onDiscard: vi.fn(),
  onSaveAndExit: vi.fn(),
};

describe("ScriptExitModal", () => {
  it("renders nothing when open=false", () => {
    const { container } = render(
      <ScriptExitModal open={false} {...noopHandlers} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders kicker, headline, and body copy when open", () => {
    render(<ScriptExitModal open {...noopHandlers} />);
    expect(screen.getByText("CHƯA LƯU")).toBeTruthy();
    expect(screen.getByText("Bạn có thay đổi chưa lưu")).toBeTruthy();
    expect(screen.getByText(/Hệ thống không tự động lưu/)).toBeTruthy();
  });

  it("Hủy + Thoát không lưu + Lưu & thoát each call their handler", () => {
    const onCancel = vi.fn();
    const onDiscard = vi.fn();
    const onSaveAndExit = vi.fn();
    render(
      <ScriptExitModal
        open
        onCancel={onCancel}
        onDiscard={onDiscard}
        onSaveAndExit={onSaveAndExit}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /^Hủy$/ }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: /Thoát không lưu/ }));
    expect(onDiscard).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: /Lưu & thoát/ }));
    expect(onSaveAndExit).toHaveBeenCalledTimes(1);
  });

  it("clicking the overlay calls onCancel", () => {
    const onCancel = vi.fn();
    const { container } = render(
      <ScriptExitModal open {...noopHandlers} onCancel={onCancel} />,
    );
    const overlay = container.querySelector('[role="dialog"]') as HTMLElement;
    fireEvent.click(overlay);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("Escape key calls onCancel", () => {
    const onCancel = vi.fn();
    render(<ScriptExitModal open {...noopHandlers} onCancel={onCancel} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("X button calls onCancel", () => {
    const onCancel = vi.fn();
    render(<ScriptExitModal open {...noopHandlers} onCancel={onCancel} />);
    fireEvent.click(screen.getByLabelText(/Đóng/));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("busy=true disables Lưu & thoát and shows 'Đang lưu…'", () => {
    render(<ScriptExitModal open busy {...noopHandlers} />);
    const cta = screen.getByRole("button", { name: /Đang lưu/ }) as HTMLButtonElement;
    expect(cta.disabled).toBe(true);
  });
});
