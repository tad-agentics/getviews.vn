import { describe, it, expect, vi } from "vitest";
import { render, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import AppLayout from "./layout";
import { useAuth } from "@/lib/auth";

vi.mock("@/lib/auth", () => ({
  useAuth: vi.fn(),
}));

describe("AppLayout auth guard", () => {
  it("redirects to /login when no user", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      session: null,
      loading: false,
      signOut: vi.fn(),
    });
    const view = render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route path="/app" element={<AppLayout />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(within(view.container).getByText("Login Page")).toBeTruthy();
    view.unmount();
  });

  it("shows spinner while loading", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      session: null,
      loading: true,
      signOut: vi.fn(),
    });
    const view = render(
      <MemoryRouter initialEntries={["/app"]}>
        <Routes>
          <Route path="/app" element={<AppLayout />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(within(view.container).queryByText("Login Page")).toBeNull();
    expect(within(view.container).getByRole("status", { name: /Đang tải/i })).toBeTruthy();
  });
});
