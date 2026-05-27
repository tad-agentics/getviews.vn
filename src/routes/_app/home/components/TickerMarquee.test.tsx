import { describe, expect, it } from "vitest";
import { tickerMarqueeRows } from "./TickerMarquee";
import type { TickerItem } from "@/hooks/useHomeTicker";

const SAMPLE: TickerItem[] = [
  {
    bucket: "breakout",
    label_vi: "BREAKOUT",
    headline_vi: "@creator · 120K views · 2.5× trung bình kênh",
    target_kind: "video",
    target_id: "1",
  },
];

describe("tickerMarqueeRows", () => {
  it("returns empty when no API items", () => {
    expect(tickerMarqueeRows([])).toEqual([]);
  });

  it("duplicates rows for marquee loop", () => {
    expect(tickerMarqueeRows(SAMPLE)).toHaveLength(2);
    expect(tickerMarqueeRows(SAMPLE)[0]).toEqual(SAMPLE[0]);
  });
});
