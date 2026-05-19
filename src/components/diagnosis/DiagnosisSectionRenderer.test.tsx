import { describe, expect, it } from "vitest";

import { mapDiagnosisEmbeddedTiles } from "./DiagnosisSectionRenderer";
import type { ReferenceVideoCard } from "@/lib/api-types";

describe("mapDiagnosisEmbeddedTiles", () => {
  it("joins aweme_id hints to reference_videos rows", () => {
    const refs: ReferenceVideoCard[] = [
      {
        aweme_id: "111",
        desc: "Caption ref",
        hook_type: null,
        content_format: "tutorial",
        views: 12000,
        engagement_rate: null,
        author_handle: "@x",
        thumbnail_url: "https://thumb/1.jpg",
        tiktok_url: "https://tiktok.com/@x/video/111",
        source: "corpus",
      },
    ];
    const tiles = mapDiagnosisEmbeddedTiles([{ aweme_id: "111" }], refs);
    expect(tiles).toHaveLength(1);
    expect(tiles[0].video_url).toContain("111");
    expect(tiles[0].views).toBe(12000);
    expect(tiles[0].caption_snippet).toContain("Caption ref");
  });

  it("drops tile hints that are not in reference_videos (hallucinated aweme_id)", () => {
    const refs: ReferenceVideoCard[] = [
      {
        aweme_id: "111",
        desc: "Caption ref",
        hook_type: null,
        content_format: null,
        views: 1000,
        engagement_rate: null,
        author_handle: null,
        thumbnail_url: "https://thumb/1.jpg",
        tiktok_url: "https://tiktok.com/@x/video/111",
        source: "corpus",
      },
    ];
    const tiles = mapDiagnosisEmbeddedTiles(
      [{ aweme_id: "999", caption_snippet: "Hallucinated caption" }],
      refs,
    );
    expect(tiles).toHaveLength(0);
  });
});
