/**
 * BUG-17 regression: every shot used to render the same dark palette
 * block. ShotTypeVisual must produce a different gradient + icon per
 * scene type so creators can scan the timeline.
 */
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ShotTypeVisual } from "./ShotTypeVisual";

describe("ShotTypeVisual", () => {
  it("renders the face_to_camera gradient when intelSceneType is canonical", () => {
    const { container } = render(
      <ShotTypeVisual intelSceneType="face_to_camera" cam="Cận mặt" />,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toMatch(/#3D2F4A/);
  });

  it("infers product_shot from a Vietnamese cam hint when intelSceneType is absent", () => {
    const { container } = render(
      <ShotTypeVisual intelSceneType={null} cam="Cận sản phẩm giữa khung" />,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toMatch(/#8A5E2F/);
  });

  it("falls back to the other gradient when no match", () => {
    const { container } = render(<ShotTypeVisual intelSceneType={null} cam="??? mystery ???" />);
    const root = container.firstChild as HTMLElement;
    // The ``other`` gradient includes ``#555``.
    expect(root.className).toMatch(/#555/);
  });

  it("shows the cam hint as the caption when provided", () => {
    const { getByText } = render(
      <ShotTypeVisual intelSceneType="broll" cam="Cắt nhanh b-roll" />,
    );
    expect(getByText("Cắt nhanh b-roll")).toBeDefined();
  });
});
