import { describe, expect, it } from "vitest";

import {
  buildDiagnosisReferenceTiles,
  buildGapLinkedTileNarrative,
  embeddedTilesFromEvidenceAnchors,
  enrichReferenceTilesForGaps,
  formatReferenceBridgeProse,
  mapDiagnosisEmbeddedTiles,
  partitionFindingsByChip,
  resolvePeerReferenceTiles,
  referenceTileNarrative,
  stripGenericReferenceBoilerplate,
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

describe("partitionFindingsByChip", () => {
  it("splits keep-advice from corrective findings", () => {
    const { strengths, gaps } = partitionFindingsByChip([
      { title_vi: "Nhịp tốt", fix_vi: "Tiếp tục giữ nhịp 1.2s/cảnh." },
      { title_vi: "Hook chậm", fix_vi: "Mở bằng câu hỏi trong 1s đầu." },
    ]);
    expect(strengths).toHaveLength(1);
    expect(gaps).toHaveLength(1);
    expect(strengths[0].title_vi).toBe("Nhịp tốt");
    expect(gaps[0].title_vi).toBe("Hook chậm");
  });

  it("routes a finding with no fix_vi to observations (not a gap)", () => {
    const { strengths, gaps, observations } = partitionFindingsByChip([
      { title_vi: "Quan sát trung tính", body_vi: "Không có hành động." },
      { title_vi: "Hook chậm", fix_vi: "Mở bằng câu hỏi trong 1s đầu." },
    ]);
    expect(strengths).toHaveLength(0);
    expect(gaps).toHaveLength(1);
    expect(observations).toHaveLength(1);
    expect(observations[0].title_vi).toBe("Quan sát trung tính");
  });
});

describe("referenceFallbackNarrative", () => {
  it("uses Vietnamese hook/format labels instead of raw enums", () => {
    const text = referenceTileNarrative({
      video_url: "",
      thumbnail_url: "",
      views: 1,
      caption_snippet: "",
      posted_at: "",
      hook_type: "question",
      content_format: "tutorial",
      narrative_vi: "short",
    });
    expect(text).toContain("Đặt Câu Hỏi");
    expect(text).toContain("Hướng dẫn");
    expect(text).not.toContain("question");
    expect(text).not.toContain("tutorial");
  });
});

describe("stripGenericReferenceBoilerplate", () => {
  it("removes generic lead and trailing angle from cached tile copy", () => {
    const raw =
      "Được chọn vì cấu trúc format và nhịp dẫn nhất quán suốt clip. So format và giữ chân suốt clip với video đang phân tích.";
    expect(stripGenericReferenceBoilerplate(raw)).toBe(
      "cấu trúc format và nhịp dẫn nhất quán suốt clip.",
    );
  });
});

describe("buildGapLinkedTileNarrative", () => {
  it("frames peer lesson against a gap title", () => {
    const text = buildGapLinkedTileNarrative(
      {
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "",
        posted_at: "",
        narrative_vi: "mở bằng câu hỏi cụ thể ngay 0s.",
      },
      { title_vi: "Hook thiếu điểm nhạy", fix_vi: "Đổi thành câu hỏi cụ thể trong 0s." },
    );
    expect(text).toContain("«Hook thiếu điểm nhạy»");
    expect(text).toContain("mở bằng câu hỏi cụ thể");
    expect(text).toContain("Áp dụng:");
  });

  it("uses structure-specific peer fallback when tile narrative is thin", () => {
    const text = buildGapLinkedTileNarrative(
      {
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "",
        posted_at: "",
      },
      { title_vi: "Dead air giữa clip", fix_vi: "Xen cận mỗi 2s." },
      "structure",
    );
    expect(text).toContain("«Dead air giữa clip»");
    expect(text).toMatch(/xen cận|nhịp cắt|dead air/i);
  });
});

describe("formatReferenceBridgeProse", () => {
  it("leads into a single reference card for one gap", () => {
    expect(
      formatReferenceBridgeProse(
        [{ title_vi: "Hook thiếu điểm nhạy" }],
        1,
      ),
    ).toContain("«Hook thiếu điểm nhạy»");
  });

  it("uses structure-specific wording for video structure block", () => {
    const text = formatReferenceBridgeProse(
      [{ title_vi: "Dead air giữa clip" }],
      1,
      "structure",
    );
    expect(text).toContain("thiếu sót");
    expect(text).toContain("nhịp/cảnh/âm");
  });
});

describe("enrichReferenceTilesForGaps", () => {
  it("overrides narrative_vi per tile", () => {
    const out = enrichReferenceTilesForGaps(
      [
        {
          video_url: "",
          thumbnail_url: "",
          views: 1,
          caption_snippet: "",
          posted_at: "",
          narrative_vi: "Được chọn vì hook câu hỏi mạnh.",
        },
      ],
      [{ title_vi: "Hook yếu", fix_vi: "Mở bằng câu hỏi." }],
    );
    expect(out[0].narrative_vi).toContain("«Hook yếu»");
    expect(out[0].narrative_vi).not.toContain("Được chọn vì");
  });
});

describe("resolvePeerReferenceTiles", () => {
  const tile = {
    video_url: "https://tiktok.com/@peer/video/111",
    thumbnail_url: "https://t/1.jpg",
    views: 100_000,
    caption_snippet: "",
    posted_at: "",
    aweme_id: "111",
    narrative_vi: "Peer làm hook tốt hơn.",
  };

  it("returns empty for diagnosis when findings are strengths-only", () => {
    expect(
      resolvePeerReferenceTiles(
        "diagnosis",
        [tile],
        [{ title_vi: "Persona tin cậy", fix_vi: "Tiếp tục giữ phong cách thật." }],
      ),
    ).toEqual([]);
  });

  it("returns gap-linked tiles for diagnosis when corrective findings exist", () => {
    const out = resolvePeerReferenceTiles(
      "diagnosis",
      [tile],
      [{ title_vi: "Hook yếu", fix_vi: "Đổi câu mở cụ thể." }],
    );
    expect(out).toHaveLength(1);
    expect(out[0].narrative_vi).toContain("«Hook yếu»");
  });

  it("does not surface peers for a no-fix finding in gap-only sections (#2)", () => {
    expect(
      resolvePeerReferenceTiles(
        "hook_analysis",
        [tile],
        [{ title_vi: "Quan sát", body_vi: "Không hành động." }],
      ),
    ).toEqual([]);
  });

  it("keeps niche_pattern tiles regardless of finding chips", () => {
    expect(
      resolvePeerReferenceTiles(
        "niche_pattern",
        [tile],
        [{ title_vi: "X", fix_vi: "Tiếp tục giữ Y." }],
      ),
    ).toHaveLength(1);
  });

  it("caps peer tiles to gap count in gap-only sections", () => {
    const extra = { ...tile, aweme_id: "222", narrative_vi: "Peer 2." };
    const out = resolvePeerReferenceTiles(
      "hook_analysis",
      [tile, extra],
      [{ title_vi: "Overlay trễ", fix_vi: "Đưa text về 0,5s." }],
    );
    expect(out).toHaveLength(1);
    expect(out[0].aweme_id).toBe("111");
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
        narrative_vi: "Được chọn vì hook câu hỏi mạnh hơn median.",
      }),
    ).toBe("Được chọn vì hook câu hỏi mạnh hơn median.");
  });

  it("strips legacy handle and view count from cached narrative", () => {
    expect(
      referenceTileNarrative({
        video_url: "",
        thumbnail_url: "",
        views: 210_200,
        caption_snippet: "",
        posted_at: "",
        narrative_vi:
          "Kênh @tuyetmia204 (210.2K view) đang vận hành cực kỳ hiệu quả. Phân tích cách video này xây dựng format.",
      }),
    ).toBe(
      "Phân tích cách video này xây dựng format.",
    );
  });
});
