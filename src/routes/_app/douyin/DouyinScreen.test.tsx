/**
 * PR-T5 — Kho Douyin stub screen render-test.
 *
 * The full Douyin surface is a separate wave; this stub ships now so
 * the TrendsDouyinCard link has a real destination. Tests assert the
 * placeholder body + back-to-Trends CTA.
 */
import { cleanup, render } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "u" },
    session: { user: { id: "u" } },
    loading: false,
    signOut: vi.fn(),
  }),
}));

const { default: DouyinScreen } = await import("./DouyinScreen");

afterEach(() => {
  cleanup();
});

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="probe">{location.pathname}</span>;
}

describe("DouyinScreen (stub)", () => {
  it("renders the placeholder kicker + heading + body", () => {
    const { getByText } = render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    expect(getByText(/TÍN HIỆU SỚM · DOUYIN → VN/)).toBeTruthy();
    expect(getByText(/Kho Douyin đang chuẩn bị/)).toBeTruthy();
    expect(getByText(/Pattern Trung Quốc đã được dịch/)).toBeTruthy();
  });

  it("offers a 'Quay lại Xu hướng' CTA that routes to /app/trends", async () => {
    const { getByText, findByTestId } = render(
      <MemoryRouter initialEntries={["/app/douyin"]}>
        <Routes>
          <Route path="/app/douyin" element={<DouyinScreen />} />
          <Route path="/app/trends" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );
    getByText(/Quay lại Xu hướng/).click();
    expect((await findByTestId("probe")).textContent).toBe("/app/trends");
  });
});
