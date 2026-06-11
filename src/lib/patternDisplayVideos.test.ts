import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: { VITE_R2_PUBLIC_URL: "https://media.getviews.vn" },
}));

import { applyPatternThumbFailure, pickPatternDisplayVideos } from "./patternDisplayVideos";

const r2 = (id: string) => `https://media.getviews.vn/thumbnails/${id}.webp`;

describe("pickPatternDisplayVideos", () => {
  it("keeps only stable R2 thumbs and sorts by views", () => {
    const { display, pool } = pickPatternDisplayVideos([
      { video_id: "a", thumbnail_url: null, views: 900 },
      { video_id: "b", thumbnail_url: "https://tiktok.cdn/x.jpg", views: 800 },
      { video_id: "c", thumbnail_url: r2("c"), views: 500 },
      { video_id: "d", thumbnail_url: r2("d"), views: 700 },
    ]);
    expect(pool.map((v) => v.video_id)).toEqual(["d", "c"]);
    expect(display.map((v) => v.video_id)).toEqual(["d", "c"]);
  });

  it("does not ping-pong between two failed thumbs in the same strip", () => {
    const row = (id: string, views: number) => ({
      video_id: id,
      thumbnail_url: r2(id),
      views,
    });
    const pool = [row("a", 400), row("b", 300), row("c", 200), row("d", 100)];
    const failedIds = new Set<string>();
    let cells = pool.slice(0, 4);

    cells = applyPatternThumbFailure(cells, "b", pool, failedIds);
    expect(cells.map((v) => v.video_id)).not.toContain("b");

    const afterSecond = applyPatternThumbFailure(cells, cells[0]!.video_id, pool, failedIds);
    expect(afterSecond.map((v) => v.video_id)).not.toContain("b");
  });

  it("caps display at four while pool keeps all stable rows", () => {
    const rows = [1, 2, 3, 4, 5, 6].map((n) => ({
      video_id: `v${n}`,
      thumbnail_url: r2(`v${n}`),
      views: n * 100,
    }));
    const { display, pool } = pickPatternDisplayVideos(rows);
    expect(pool).toHaveLength(6);
    expect(display).toHaveLength(4);
    expect(display[0]?.video_id).toBe("v6");
  });
});
