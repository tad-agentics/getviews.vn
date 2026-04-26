/**
 * PR-4 Studio Home — ChannelBridgeRibbon render-test.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChannelBridgeRibbon } from "./ChannelBridgeRibbon";

afterEach(() => {
  cleanup();
});

describe("ChannelBridgeRibbon", () => {
  it("renders the kicker, body sentence, and CTA button", () => {
    const { getByText } = render(
      <ChannelBridgeRibbon onScrollToSuggestions={() => {}} />,
    );
    expect(getByText("→ TIẾP THEO")).toBeTruthy();
    expect(
      getByText(/Gợi ý hôm nay đã ưu tiên các ý tưởng bám theo/),
    ).toBeTruthy();
    expect(getByText(/Xem gợi ý ↓/)).toBeTruthy();
  });

  it("invokes onScrollToSuggestions when the CTA is clicked", () => {
    const onScroll = vi.fn();
    const { getByText } = render(
      <ChannelBridgeRibbon onScrollToSuggestions={onScroll} />,
    );
    fireEvent.click(getByText(/Xem gợi ý ↓/));
    expect(onScroll).toHaveBeenCalledOnce();
  });

  it("uses ink fill on the section and accent fill on the CTA", () => {
    const { getByText } = render(
      <ChannelBridgeRibbon onScrollToSuggestions={() => {}} />,
    );
    const cta = getByText(/Xem gợi ý ↓/);
    expect(cta.className).toMatch(/gv-accent/);
    // The section is the closest ancestor that carries the ink fill.
    const section = cta.closest("section");
    expect(section?.className).toMatch(/gv-ink/);
  });
});
