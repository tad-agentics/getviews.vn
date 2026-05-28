import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CorpusVideoPreviewDialog } from "./CorpusVideoPreviewDialog";

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogClose: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}));

describe("CorpusVideoPreviewDialog", () => {
  it("renders R2 video player when video_url is present", () => {
    const { container } = render(
      <CorpusVideoPreviewDialog
        open
        video={{
          video_id: "7633003576469523733",
          title: "Review váy",
          subtitle: "@shop · ↑ 2.1M",
          thumbnail_url: "https://t/thumb.jpg",
          tiktok_url: "https://www.tiktok.com/@shop/video/7633003576469523733",
          video_url: "https://cdn.example/videos/7633003576469523733.mp4",
        }}
        onOpenChange={() => {}}
        onAnalyze={() => {}}
      />,
    );

    const video = container.querySelector("video");
    expect(video).toBeTruthy();
    expect(video?.getAttribute("src")).toContain("7633003576469523733");
    expect(container.querySelector("iframe")).toBeNull();
  });
});
