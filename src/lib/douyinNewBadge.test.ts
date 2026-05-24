import { describe, expect, it, beforeEach } from "vitest";
import {
  countDouyinNewVideos,
  formatDouyinNewBadge,
  markDouyinFeedVisited,
  readDouyinLastVisitAt,
  seedDouyinVisitBaselineIfAbsent,
} from "./douyinNewBadge";

describe("douyinNewBadge", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns 0 when no visit baseline exists (avoid whole-corpus badge)", () => {
    const count = countDouyinNewVideos([
      { video_id: "a", indexed_at: "2026-05-21T00:00:00Z" },
    ] as Parameters<typeof countDouyinNewVideos>[0]);
    expect(count).toBe(0);
  });

  it("counts videos indexed after last visit", () => {
    markDouyinFeedVisited(new Date("2026-05-20T00:00:00Z"));
    const count = countDouyinNewVideos(
      [
        { video_id: "a", indexed_at: "2026-05-19T00:00:00Z" },
        { video_id: "b", indexed_at: "2026-05-21T00:00:00Z" },
      ] as Parameters<typeof countDouyinNewVideos>[0],
    );
    expect(count).toBe(1);
  });

  it("seeds baseline only once", () => {
    seedDouyinVisitBaselineIfAbsent(new Date("2026-05-01T00:00:00Z"));
    seedDouyinVisitBaselineIfAbsent(new Date("2026-06-01T00:00:00Z"));
    expect(readDouyinLastVisitAt()).toBe(new Date("2026-05-01T00:00:00Z").getTime());
  });

  it("formatDouyinNewBadge caps at 99+", () => {
    expect(formatDouyinNewBadge(0)).toBeUndefined();
    expect(formatDouyinNewBadge(3)).toBe("🇨🇳 3 MỚI");
    expect(formatDouyinNewBadge(100)).toBe("🇨🇳 99+ MỚI");
  });
});
