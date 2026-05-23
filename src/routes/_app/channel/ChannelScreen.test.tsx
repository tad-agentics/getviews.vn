import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router";
import { render, screen, waitFor } from "@testing-library/react";

import ChannelScreen from "./ChannelScreen";

function SearchCapture() {
  const [params] = useSearchParams();
  return <div data-testid="search">{params.toString()}</div>;
}

describe("ChannelScreen redirect", () => {
  it("redirects /app/channel to /app preserving query params", async () => {
    render(
      <MemoryRouter initialEntries={["/app/channel?handle=foo&depth=sau"]}>
        <Routes>
          <Route path="/app/channel" element={<ChannelScreen />} />
          <Route path="/app" element={<SearchCapture />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("search").textContent).toBe("handle=foo&depth=sau");
    });
  });
});
