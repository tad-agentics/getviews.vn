import { describe, expect, it } from "vitest";
import { tickerMarqueeRows, uniqueTickerItems } from "./TickerMarquee";
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

  it("keeps a single unique row without duplicating (static strip)", () => {
    expect(tickerMarqueeRows(SAMPLE)).toEqual(SAMPLE);
  });

  it("duplicates rows for marquee loop when 2+ unique items", () => {
    const two = [
      SAMPLE[0],
      { ...SAMPLE[0], bucket: "hook_mới" as const, label_vi: "HOOK MỚI", target_id: "2" },
    ];
    expect(tickerMarqueeRows(two)).toHaveLength(4);
  });
});
