import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return { ...actual, useNavigate: () => mockNavigate };
});

const { OffTaxonomyBanner } = await import("./OffTaxonomyBanner");

afterEach(() => {
  cleanup();
  mockNavigate.mockReset();
});

describe("OffTaxonomyBanner", () => {
  it("rewrites legacy /app/script deeplink to Answer composer prefill", () => {
    render(
      <MemoryRouter>
        <OffTaxonomyBanner
          data={{
            suggestions: [
              {
                label: "Viết kịch bản",
                route: "/app/script?topic=Test+hook&duration=32",
              },
            ],
          }}
        />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: /Viết kịch bản/i }));
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    const path = mockNavigate.mock.calls[0][0] as string;
    expect(path).toMatch(/^\/app\/answer\?q=/);
  });

  it("rewrites legacy shoot route to Answer ?shoot=", () => {
    render(
      <MemoryRouter>
        <OffTaxonomyBanner
          data={{
            suggestions: [
              {
                label: "Quay",
                route: "/app/script/shoot/draft-42?session=sess-1",
              },
            ],
          }}
        />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: /Quay/i }));
    const path = mockNavigate.mock.calls[0][0] as string;
    expect(path).toContain("shoot=draft-42");
    expect(path).toContain("session=sess-1");
  });
});
