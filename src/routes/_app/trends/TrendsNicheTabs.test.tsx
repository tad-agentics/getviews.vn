/**
 * PR-T1 Trends — TrendsNicheTabs render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 298-328.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { NicheWithHot } from "@/hooks/useTopNiches";
import { TrendsNicheTabs } from "./TrendsNicheTabs";

afterEach(() => {
  cleanup();
});

const sample: NicheWithHot[] = [
  { id: 4, name: "Ẩm thực", hot: 124 },
  { id: 7, name: "Công nghệ", hot: 86 },
  { id: 12, name: "Làm đẹp", hot: 240 },
];

describe("TrendsNicheTabs", () => {
  it("renders nothing when only one niche is followed", () => {
    const { container } = render(
      <TrendsNicheTabs
        niches={[sample[0]]}
        selectedNicheId={4}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    expect(container.querySelector('[role="tablist"]')).toBeNull();
  });

  it("renders nothing when followed niches array is empty", () => {
    const { container } = render(
      <TrendsNicheTabs
        niches={[]}
        selectedNicheId={null}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    expect(container.querySelector('[role="tablist"]')).toBeNull();
  });

  it("renders one tab per followed niche when ≥ 2", () => {
    const { getAllByRole } = render(
      <TrendsNicheTabs
        niches={sample}
        selectedNicheId={4}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    const tabs = getAllByRole("tab");
    expect(tabs).toHaveLength(3);
    expect(tabs.map((t) => t.textContent)).toEqual(["Ẩm thực", "Công nghệ", "Làm đẹp"]);
  });

  it("marks the matching niche as the active tab", () => {
    const { getAllByRole } = render(
      <TrendsNicheTabs
        niches={sample}
        selectedNicheId={7}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    const tabs = getAllByRole("tab");
    expect(tabs[0].getAttribute("aria-selected")).toBe("false");
    expect(tabs[1].getAttribute("aria-selected")).toBe("true");
    expect(tabs[1].className).toMatch(/border-\[color:var\(--gv-ink\)\]/);
  });

  it("invokes onSelectNiche with the chosen id when a tab is clicked", () => {
    const onSelect = vi.fn();
    const { getAllByRole } = render(
      <TrendsNicheTabs
        niches={sample}
        selectedNicheId={4}
        onSelectNiche={onSelect}
        onEditNiches={() => {}}
      />,
    );
    fireEvent.click(getAllByRole("tab")[2]); // Làm đẹp
    expect(onSelect).toHaveBeenCalledWith(12);
  });

  it("invokes onEditNiches when the trailing link is clicked", () => {
    const onEdit = vi.fn();
    const { getByText } = render(
      <TrendsNicheTabs
        niches={sample}
        selectedNicheId={4}
        onSelectNiche={() => {}}
        onEditNiches={onEdit}
      />,
    );
    fireEvent.click(getByText(/\+ Đổi ngách đang theo dõi/));
    expect(onEdit).toHaveBeenCalledOnce();
  });

  it("renders the NGÁCH BẠN THEO DÕI mono kicker", () => {
    const { getByText } = render(
      <TrendsNicheTabs
        niches={sample}
        selectedNicheId={4}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    expect(getByText("NGÁCH BẠN THEO DÕI")).toBeTruthy();
  });
});
