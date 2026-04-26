/**
 * PR-2 Studio Home — ChannelDiagnosticList render-test.
 *
 * BE source-of-truth:
 * ``cloud-run/getviews_pipeline/channel_analyze.py::ChannelStrengthLLM``
 * + ``ChannelWeaknessLLM``.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ChannelDiagnosticItem } from "@/lib/api-types";
import { ChannelDiagnosticList } from "./ChannelDiagnosticList";

afterEach(() => {
  cleanup();
});

const strength: ChannelDiagnosticItem = {
  title: "Hook 0.8s bám trend đang lên",
  metric: "Hook < 1s · 80% video",
  why: "Audience của ngách Tech quyết định scroll trong 0.8s.",
  action: "Tiếp tục mở bằng face cam, đẩy CTA xuống cuối.",
  bridge_to: "01",
};

const weakness: ChannelDiagnosticItem = {
  title: "Retention 3s đang dưới ngách",
  metric: "Retention 0.42 · ngách 0.55",
  why: "Câu mở thiếu hook number/curiosity.",
  action: "Rút opening còn 3 từ, đặt số ở câu đầu.",
  bridge_to: "02",
};

describe("ChannelDiagnosticList", () => {
  it("renders nothing when items is empty", () => {
    const { container } = render(<ChannelDiagnosticList kind="strength" items={[]} />);
    expect(container.querySelector("ul")).toBeNull();
  });

  it("renders title, metric, why, and TẬN DỤNG action for strengths", () => {
    const { getByText } = render(<ChannelDiagnosticList kind="strength" items={[strength]} />);
    expect(getByText(/Hook 0\.8s bám trend/)).toBeTruthy();
    expect(getByText(/Hook < 1s · 80% video/)).toBeTruthy();
    expect(getByText(/Audience của ngách Tech/)).toBeTruthy();
    expect(getByText(/Tiếp tục mở bằng face cam/)).toBeTruthy();
    expect(getByText(/TẬN DỤNG/)).toBeTruthy();
  });

  it("renders CÁCH SỬA action label for weaknesses", () => {
    const { getByText, queryByText } = render(
      <ChannelDiagnosticList kind="weakness" items={[weakness]} />,
    );
    expect(getByText(/CÁCH SỬA/)).toBeTruthy();
    expect(queryByText(/TẬN DỤNG/)).toBeNull();
  });

  it("uses pos-deep tone for strengths metric and neg-deep for weaknesses", () => {
    const { getByText: getStrength } = render(
      <ChannelDiagnosticList kind="strength" items={[strength]} />,
    );
    expect(getStrength(strength.metric).className).toMatch(/gv-pos-deep/);
    cleanup();
    const { getByText: getWeakness } = render(
      <ChannelDiagnosticList kind="weakness" items={[weakness]} />,
    );
    expect(getWeakness(weakness.metric).className).toMatch(/gv-neg-deep/);
  });

  it("renders the bridge pill and forwards onBridgeClick with the tier id", () => {
    const onBridgeClick = vi.fn();
    const { getByText } = render(
      <ChannelDiagnosticList
        kind="strength"
        items={[strength]}
        onBridgeClick={onBridgeClick}
      />,
    );
    const pill = getByText(/→ 01/);
    fireEvent.click(pill);
    expect(onBridgeClick).toHaveBeenCalledWith("01");
  });

  it("hides the bridge pill when bridge_to is null", () => {
    const noBridge: ChannelDiagnosticItem = { ...strength, bridge_to: null };
    const { queryByText } = render(
      <ChannelDiagnosticList kind="strength" items={[noBridge]} />,
    );
    expect(queryByText(/→/)).toBeNull();
  });

  it("hides the metric line when item.metric is empty", () => {
    const noMetric: ChannelDiagnosticItem = { ...strength, metric: "" };
    const { queryByText } = render(
      <ChannelDiagnosticList kind="strength" items={[noMetric]} />,
    );
    expect(queryByText(/Hook < 1s/)).toBeNull();
  });
});
