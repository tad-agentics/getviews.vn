import React from "react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useProfile", () => ({
  useProfile: () => ({
    data: { creator_niche_id: 1, credits_remaining: 10, tiktok_handle: "mychannel" },
    isPending: false,
  }),
}));

vi.mock("@/routes/_app/channel/components/ChannelStudioPanel", () => ({
  ChannelStudioPanel: () => <div data-testid="channel-panel">panel</div>,
}));

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import ChannelScreen from "./ChannelScreen";

describe("ChannelScreen", () => {
  it("renders full-page channel panel", () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/app/channel?handle=foo"]}>
          <ChannelScreen />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText("Khám kênh TikTok")).toBeTruthy();
    expect(screen.getByTestId("channel-panel")).toBeTruthy();
  });
});
