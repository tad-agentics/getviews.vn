/**
 * PR-5 Studio Home — NichePicker render-test.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { NicheWithHot } from "@/hooks/useTopNiches";
import { NichePicker } from "./NichePicker";

afterEach(() => {
  cleanup();
});

const niches: NicheWithHot[] = [
  { id: 4, name: "Ẩm thực", hot: 124 },
  { id: 7, name: "Công nghệ", hot: 86 },
  { id: 12, name: "Làm đẹp", hot: 240 },
];

describe("NichePicker", () => {
  it("renders nothing when there are no niches", () => {
    const { container } = render(
      <NichePicker
        niches={[]}
        selectedNicheId={null}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    expect(container.querySelector("button")).toBeNull();
  });

  it("renders a static chip (no button) when only 1 niche", () => {
    const { queryByRole, getByLabelText } = render(
      <NichePicker
        niches={[niches[0]]}
        selectedNicheId={4}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    expect(queryByRole("button")).toBeNull();
    expect(getByLabelText("Ngách đang theo dõi")).toBeTruthy();
  });

  it("opens the dropdown on click and lists each niche option", () => {
    const onSelect = vi.fn();
    const { getByRole, getAllByRole, queryByRole } = render(
      <NichePicker
        niches={niches}
        selectedNicheId={4}
        onSelectNiche={onSelect}
        onEditNiches={() => {}}
      />,
    );
    // Closed → no listbox.
    expect(queryByRole("listbox")).toBeNull();
    fireEvent.click(getByRole("button", { name: /Ẩm thực/ }));
    const opts = getAllByRole("option");
    expect(opts).toHaveLength(3);
    expect(opts[0].textContent).toContain("Ẩm thực");
    // Selected option carries aria-selected.
    expect(opts[0].getAttribute("aria-selected")).toBe("true");
    expect(opts[1].getAttribute("aria-selected")).toBe("false");
  });

  it("invokes onSelectNiche with the chosen id and closes the panel", () => {
    const onSelect = vi.fn();
    const { getByRole, getAllByRole, queryByRole } = render(
      <NichePicker
        niches={niches}
        selectedNicheId={4}
        onSelectNiche={onSelect}
        onEditNiches={() => {}}
      />,
    );
    fireEvent.click(getByRole("button", { name: /Ẩm thực/ }));
    fireEvent.click(getAllByRole("option")[1]); // Công nghệ
    expect(onSelect).toHaveBeenCalledWith(7);
    expect(queryByRole("listbox")).toBeNull();
  });

  it("invokes onEditNiches when the footer link is clicked", () => {
    const onEdit = vi.fn();
    const { getByRole, getByText } = render(
      <NichePicker
        niches={niches}
        selectedNicheId={4}
        onSelectNiche={() => {}}
        onEditNiches={onEdit}
      />,
    );
    fireEvent.click(getByRole("button", { name: /Ẩm thực/ }));
    fireEvent.click(getByText(/\+ Đổi ngách đang theo dõi/));
    expect(onEdit).toHaveBeenCalledOnce();
  });

  it("hides the hot count fragment on the trigger when count is 0", () => {
    const cold: NicheWithHot[] = [
      { id: 4, name: "Ẩm thực", hot: 0 },
      { id: 7, name: "Công nghệ", hot: 0 },
    ];
    const { getByRole, queryByText } = render(
      <NichePicker
        niches={cold}
        selectedNicheId={4}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    // Multi-niche → button rendered, but no "↓ X hot" fragment.
    expect(getByRole("button", { name: /Ẩm thực/ })).toBeTruthy();
    expect(queryByText(/hot/)).toBeNull();
  });

  it("falls back to the first niche when selectedNicheId doesn't match", () => {
    const { getByRole } = render(
      <NichePicker
        niches={niches}
        selectedNicheId={999}
        onSelectNiche={() => {}}
        onEditNiches={() => {}}
      />,
    );
    // First niche's name shows on the button.
    expect(getByRole("button", { name: /Ẩm thực/ })).toBeTruthy();
  });
});
