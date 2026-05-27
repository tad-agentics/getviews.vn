import { describe, expect, it } from "vitest";
import { MIN_TICKER_UNIQUE_ITEMS, tickerMarqueeRows, uniqueTickerItems } from "./TickerMarquee";
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

describe("uniqueTickerItems", () => {
  it("drops duplicate bucket+target rows", () => {
    const dup = [...SAMPLE, ...SAMPLE];
    expect(uniqueTickerItems(dup)).toHaveLength(1);
  });
});

describe("tickerMarqueeRows", () => {
  it("returns empty when no API items", () => {
    expect(tickerMarqueeRows([])).toEqual([]);
  });

  it("returns empty when fewer than MIN unique items (avoids one-line loop)", () => {
    expect(tickerMarqueeRows(SAMPLE)).toEqual([]);
    expect(MIN_TICKER_UNIQUE_ITEMS).toBe(3);
  });

  it("duplicates rows for marquee loop when enough unique items", () => {
    const three = [
      SAMPLE[0],
      { ...SAMPLE[0], bucket: "hook_mới" as const, label_vi: "HOOK MỚI", target_id: "2" },
      { ...SAMPLE[0], bucket: "âm_thanh" as const, label_vi: "ÂM THANH", target_id: "3" },
    ];
    expect(tickerMarqueeRows(three)).toHaveLength(6);
  });
});
