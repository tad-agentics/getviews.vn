import { describe, expect, it } from "vitest";
import {
  answerSessionListTitle,
  answerSessionSidebarLabel,
  channelSidebarLabel,
} from "./answerSessionListTitle";

describe("answerSessionListTitle", () => {
  it("prefers initial_q when title is a short trailing suffix (ISSUE-014)", () => {
    expect(
      answerSessionListTitle("này", "Cảm ơn bạn đã xem video này"),
    ).toBe("Cảm ơn bạn đã xem video này");
  });
});

describe("answerSessionSidebarLabel", () => {
  it("shows @handle · video tail instead of truncated URL", () => {
    expect(
      answerSessionSidebarLabel({
        title: "https://www.tiktok.com/@minh_creator/video/7634391245737053447",
        initial_q: "https://www.tiktok.com/@minh_creator/video/7634391245737053447",
        intent_type: "video_diagnosis",
        format: "video",
      }),
    ).toBe("@minh_creator · …053447");
  });

  it("disambiguates identical flop boilerplate with TikTok identity", () => {
    const url = "https://www.tiktok.com/@shop_a/video/7634391245737053447";
    expect(
      answerSessionSidebarLabel({
        title: "Video của mình flop — phân tích nguyên nhân và nên chỉnh gì?",
        initial_q: url,
        intent_type: "video_diagnosis",
        format: "video",
      }),
    ).toBe("Video · @shop_a · …053447");
  });

  it("respects user rename label", () => {
    expect(
      answerSessionSidebarLabel({
        label: "Clip Shopee tuần 3",
        title: "https://www.tiktok.com/@x/video/1",
        initial_q: "https://www.tiktok.com/@x/video/1",
      }),
    ).toBe("Clip Shopee tuần 3");
  });
});

describe("channelSidebarLabel", () => {
  it("prefixes @ on bare handle", () => {
    expect(channelSidebarLabel("minh_shop")).toBe("@minh_shop");
  });
});
