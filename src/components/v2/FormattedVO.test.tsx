/**
 * FormattedVO tests — S5 stress-word renderer.
 * Per design pack ``screens/script.jsx`` lines 1234-1250.
 */

import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { FormattedVO } from "./FormattedVO";

afterEach(cleanup);

describe("FormattedVO", () => {
  it("renders plain text without markers as-is", () => {
    render(<FormattedVO text="Bình thường không có gì" />);
    expect(screen.getByText("Bình thường không có gì")).toBeTruthy();
  });

  it("wraps *stress* markers in <strong> with accent-soft background", () => {
    const { container } = render(
      <FormattedVO text="Mình *vừa test* xong rồi đây" />,
    );
    const strong = container.querySelector("strong");
    expect(strong).toBeTruthy();
    expect(strong?.textContent).toBe("vừa test");
    expect(strong?.className).toMatch(/gv-accent-soft/);
  });

  it("supports multiple stress markers in one line", () => {
    const { container } = render(
      <FormattedVO text="200k: *bí*. 2 triệu: *thoáng*." />,
    );
    const strongs = container.querySelectorAll("strong");
    expect(strongs.length).toBe(2);
    expect(strongs[0]?.textContent).toBe("bí");
    expect(strongs[1]?.textContent).toBe("thoáng");
  });

  it("does NOT wrap empty markers (**)", () => {
    const { container } = render(<FormattedVO text="Test ** mãi mãi" />);
    expect(container.querySelector("strong")).toBeNull();
    // Stray asterisks render literally.
    expect(container.textContent).toContain("**");
  });

  it("renders nothing for empty text", () => {
    const { container } = render(<FormattedVO text="" />);
    expect(container.firstChild).toBeNull();
  });

  it("does not cross newlines for marker matching", () => {
    // Marker spanning a newline shouldn't bold — stress is per-line.
    const { container } = render(
      <FormattedVO text={"Mình *vừa\ntest* xong"} />,
    );
    expect(container.querySelector("strong")).toBeNull();
  });
});
