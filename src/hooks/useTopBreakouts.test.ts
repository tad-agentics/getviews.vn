import { describe, expect, it } from "vitest";

import { pickRotatingBreakoutWindow } from "./useTopBreakouts";

describe("pickRotatingBreakoutWindow", () => {
  const pool = [
    { video_id: "a" },
    { video_id: "b" },
    { video_id: "c" },
    { video_id: "d" },
    { video_id: "e" },
  ];
  const ROT = 15 * 60 * 1000;

  it("returns full pool when length <= limit", () => {
    expect(pickRotatingBreakoutWindow(pool.slice(0, 2), 3, 0, ROT)).toEqual(pool.slice(0, 2));
  });

  it("rotates start index in a 15m bucket", () => {
    const a = pickRotatingBreakoutWindow(pool, 3, 0, ROT);
    const b = pickRotatingBreakoutWindow(pool, 3, ROT, ROT);
    expect(a).toHaveLength(3);
    expect(b).toHaveLength(3);
    expect(a[0]!.video_id).not.toBe(b[0]!.video_id);
  });

  it("is stable within the same rotation bucket", () => {
    const a = pickRotatingBreakoutWindow(pool, 3, 1000, ROT);
    const b = pickRotatingBreakoutWindow(pool, 3, 2000, ROT);
    expect(a.map((x) => x.video_id)).toEqual(b.map((x) => x.video_id));
  });
});
