import { describe, expect, it } from "vitest";

import {
  buildDiagnosisReferenceTiles,
  embeddedTilesFromEvidenceAnchors,
  mapDiagnosisEmbeddedTiles,
  referenceTileNarrative,
  stripSectionProseForEmbeddedRefs,
} from "./diagnosisReferenceTiles";
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
    const tiles = mapDiagnosisEmbeddedTiles(
      [
        {
          aweme_id: "111",
          narrative_vi: "Cùng chủ đề grand opening — hook số liệu mạnh hơn bạn 2,4×.",
        },
      ],
      refs,
    );
    expect(tiles).toHaveLength(1);
    expect(tiles[0].video_url).toContain("111");
    expect(tiles[0].views).toBe(12000);
    expect(tiles[0].narrative_vi).toContain("grand opening");
    expect(tiles[0].author_handle).toBe("@x");
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

describe("embeddedTilesFromEvidenceAnchors", () => {
  const PEER_ID = "7634391245737053447";
  const refs: ReferenceVideoCard[] = [
    {
      aweme_id: PEER_ID,
      desc: "Peer caption",
      hook_type: null,
      content_format: null,
      views: 5000,
      engagement_rate: null,
      author_handle: "@peer",
      thumbnail_url: "https://thumb/peer.jpg",
      tiktok_url: `https://tiktok.com/@peer/video/${PEER_ID}`,
      source: "corpus",
    },
  ];

  it("maps aweme_id anchors for matching section", () => {
    const tiles = embeddedTilesFromEvidenceAnchors(
      [{ type: "aweme_id", quote: PEER_ID, section_id: "diagnosis" }],
      refs,
      "diagnosis",
    );
    expect(tiles).toHaveLength(1);
    expect(tiles[0].video_url).toContain(PEER_ID);
  });

  it("ignores non-aweme anchors", () => {
    const tiles = embeddedTilesFromEvidenceAnchors(
      [{ type: "channel_field", quote: "median_views=1" }],
      refs,
      "diagnosis",
    );
    expect(tiles).toHaveLength(0);
  });
});

describe("buildDiagnosisReferenceTiles", () => {
  it("caps at three reference videos per section", () => {
    const refs: ReferenceVideoCard[] = Array.from({ length: 5 }, (_, i) => ({
      aweme_id: String(100 + i),
      desc: `v${i}`,
      hook_type: null,
      content_format: null,
      views: 1000,
      engagement_rate: null,
      author_handle: `@u${i}`,
      thumbnail_url: `https://t/${i}.jpg`,
      tiktok_url: `https://tiktok.com/v/${i}`,
      source: "corpus" as const,
    }));
    const tiles = buildDiagnosisReferenceTiles(
      {
        section_id: "diagnosis",
        embedded_tiles: refs.map((r) => ({ aweme_id: r.aweme_id })),
      },
      refs,
    );
    expect(tiles).toHaveLength(3);
  });
});

describe("stripSectionProseForEmbeddedRefs", () => {
  it("removes generic trailing lead-in to embedded videos", () => {
    const text =
      "Hook mở bằng câu hỏi đối lập với median ngách.\n\nVideo dưới đây cho thấy cách creator trong ngách đang áp dụng hook này hiệu quả.";
    expect(stripSectionProseForEmbeddedRefs(text)).toBe(
      "Hook mở bằng câu hỏi đối lập với median ngách.",
    );
  });
});

describe("referenceTileNarrative", () => {
  it("prefers narrative_vi over caption fallback", () => {
    expect(
      referenceTileNarrative({
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "caption",
        posted_at: "",
        narrative_vi: "So sánh cụ thể với video 34K view.",
      }),
    ).toBe("So sánh cụ thể với video 34K view.");
  });
});
