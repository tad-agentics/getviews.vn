/**
 * NextVideoCard — number-formatting guard.
 *
 * Live bug (2026-06-12): the GỢI Ý box rendered "Peer TB ~0 view" when the
 * peer row came from the enrich fallback (avg_views=0). The peer-average
 * clause must be hidden when the value is 0/null.
 */
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { ChannelNextVideoConcept } from "@/lib/api-types";

vi.mock("@/components/VideoThumbnail", () => ({
  VideoThumbnail: () => <div data-testid="thumb" />,
}));

import { NextVideoCard } from "./NextVideoCard";

afterEach(cleanup);

function makeConcept(overrides: Partial<ChannelNextVideoConcept> = {}): ChannelNextVideoConcept {
  return {
    format: "talking_head",
    format_label: "Nói trước camera",
    duration_sec: 18,
    rationale_struct: "@peer đang chạy format này; bạn chỉ có 2/60 video cùng format (~3%).",
    sample_peer_handle: "peer",
    sample_video_url: "https://www.tiktok.com/@peer/video/7123456789012345678",
    sample_thumbnail_url: null,
    peer_avg_views: 120_000,
    channel_share_pct: 3,
    ...overrides,
  };
}

describe("NextVideoCard", () => {
  it("shows the peer-average clause when peer_avg_views is real", () => {
    render(<NextVideoCard concept={makeConcept()} />);
    expect(screen.getByText(/Peer TB/)).toBeTruthy();
    expect(screen.getByText("~120K")).toBeTruthy();
  });

  it("hides the peer-average clause when peer_avg_views is 0", () => {
    render(<NextVideoCard concept={makeConcept({ peer_avg_views: 0 })} />);
    expect(screen.queryByText(/Peer TB/)).toBeNull();
    expect(screen.queryByText(/~0/)).toBeNull();
  });

  it("hides the peer-average clause when peer_avg_views is null at runtime", () => {
    render(
      <NextVideoCard
        concept={makeConcept({ peer_avg_views: null as unknown as number })}
      />,
    );
    expect(screen.queryByText(/Peer TB/)).toBeNull();
  });

  it("shows the gap clause when channel_share_pct is real", () => {
    render(<NextVideoCard concept={makeConcept()} />);
    expect(screen.getByText(/gap/)).toBeTruthy();
    expect(screen.getByText("3%")).toBeTruthy();
  });

  it("hides the gap clause when channel_share_pct is 0 (v6 answer-session path)", () => {
    render(<NextVideoCard concept={makeConcept({ channel_share_pct: 0 })} />);
    expect(screen.queryByText(/gap/)).toBeNull();
    expect(screen.queryByText(/format trên kênh/)).toBeNull();
  });

  it("hides the gap clause when channel_share_pct is null at runtime", () => {
    render(
      <NextVideoCard
        concept={makeConcept({ channel_share_pct: null as unknown as number })}
      />,
    );
    expect(screen.queryByText(/gap/)).toBeNull();
  });
});
