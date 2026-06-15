import { describe, expect, it } from "vitest";

import {
  buildDiagnosisReferenceTiles,
  buildFindingInlinePeerProse,
  buildGapLinkedTileNarrative,
  embeddedTilesFromEvidenceAnchors,
  enrichReferenceTilesForGaps,
  formatReferenceBridgeProse,
  formatNichePatternBridgeProse,
  formatSingleGapBridgeProse,
  fallbackNichePatternReferenceTiles,
  mapDiagnosisEmbeddedTiles,
  partitionFindingsByChip,
  peerTilesForGapAtIndex,
  ReferenceTileAllocator,
  referenceHasVisibleThumbnail,
  resolvePeerReferenceTiles,
  referenceTileNarrative,
  sanitizeReferenceCaptionSnippet,
  stripGenericReferenceBoilerplate,
  stripSectionProseForEmbeddedRefs,
  sectionProseHasNichePatternBridge,
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

  it("maps peer_hook_start_sec from reference_videos for MOMENT deep-link", () => {
    const refs: ReferenceVideoCard[] = [
      {
        aweme_id: "222",
        desc: null,
        hook_type: "question",
        content_format: null,
        views: 9000,
        engagement_rate: null,
        author_handle: "peer",
        thumbnail_url: "https://thumb/2.jpg",
        tiktok_url: "https://tiktok.com/@peer/video/222",
        playback_url: "https://cdn/videos/222.mp4",
        peer_hook_start_sec: 0.4,
        source: "corpus",
      },
    ];
    const tiles = mapDiagnosisEmbeddedTiles([{ aweme_id: "222" }], refs);
    expect(tiles[0].peer_hook_start_sec).toBe(0.4);
    expect(tiles[0].playback_url).toContain("222.mp4");
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

  it("omits gap title frame when inline bridge prose is shown above the tile", () => {
    const text = buildGapLinkedTileNarrative(
      {
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "",
        posted_at: "",
        narrative_vi:
          "cấu trúc format và nhịp dẫn nhất quán suốt clip. So 3 giây đầu với clip đang phân tích.",
      },
      { title_vi: "Nhịp độ mở đầu — Cần nhanh", fix_vi: "Cắt bỏ lời chào, vào ngay hành động." },
      "hook",
      { leadWithGapTitle: false },
    );
    expect(text).not.toMatch(/Để xử lý «/);
    expect(text).toMatch(/cấu trúc format và nhịp dẫn nhất quán/i);
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

describe("formatSingleGapBridgeProse", () => {
  it("uses hook-specific lead-in without repeating tile gap frame", () => {
    const text = formatSingleGapBridgeProse("Nhịp độ mở đầu — Cần nhanh", "hook");
    expect(text).toContain("Thiếu sót «Nhịp độ mở đầu — Cần nhanh»");
    expect(text).toContain("So cắt, chữ overlay");
    expect(text).not.toContain("Để khắc phục");
  });
});

describe("buildFindingInlinePeerProse", () => {
  it("weaves peer lesson and compare line into finding body prose", () => {
    const text = buildFindingInlinePeerProse(
      { title_vi: "Thiếu nhịp cắt", fix_vi: "Thêm cú cắt giật." },
      [
        {
          video_url: "https://tiktok.com/@peer/video/1",
          thumbnail_url: "https://t/1.jpg",
          views: 100_000,
          caption_snippet: "",
          posted_at: "",
          author_handle: "peer",
          narrative_vi:
            "Cấu trúc định dạng và nhịp dẫn nhất quán suốt clip. Áp dụng: thêm cú cắt.",
        },
      ],
      "hook",
    );
    expect(text).toContain("@peer");
    expect(text).toContain("So 3 giây đầu");
    expect(text).not.toContain("Áp dụng:");
  });

  it("weaves per-tile lessons when multiple peers attach to one gap", () => {
    const text = buildFindingInlinePeerProse(
      { title_vi: "Dead air", fix_vi: "Xen cận." },
      [
        {
          video_url: "https://tiktok.com/@peer1/video/1",
          thumbnail_url: "https://t/1.jpg",
          views: 100_000,
          caption_snippet: "",
          posted_at: "",
          author_handle: "peer1",
          narrative_vi: "Xen cận mỗi 2 giây suốt clip.",
        },
        {
          video_url: "https://tiktok.com/@peer2/video/2",
          thumbnail_url: "https://t/2.jpg",
          views: 80_000,
          caption_snippet: "",
          posted_at: "",
          author_handle: "peer2",
          narrative_vi: "Text overlay thay dead air ở giữa clip.",
        },
      ],
      "structure",
    );
    expect(text).toContain("Với **Dead air**:");
    expect(text).toContain("@peer1");
    expect(text).toContain("@peer2");
    expect(text).toContain("xen cận");
    expect(text).toContain("Đối chiếu nhịp cắt");
    expect(text).toMatch(/@peer1[\s\S]*\n\n[\s\S]*@peer2/);
  });
});

describe("peerTilesForGapAtIndex", () => {
  it("returns all reference tiles when section has a single gap", () => {
    const tiles = [
      {
        aweme_id: "1",
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "",
        posted_at: "",
      },
      {
        aweme_id: "2",
        video_url: "",
        thumbnail_url: "",
        views: 2,
        caption_snippet: "",
        posted_at: "",
      },
    ];
    const gaps = [{ title_vi: "Gap A", fix_vi: "Fix A." }];
    const out = peerTilesForGapAtIndex(0, gaps, tiles, "structure", true);
    expect(out).toHaveLength(2);
  });

  it("inline enrich omits gap-title bridge framing on tile narratives", () => {
    const tiles = [
      {
        aweme_id: "1",
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "",
        posted_at: "",
        narrative_vi: "Nhịp cắt chặt suốt clip.",
      },
    ];
    const gaps = [{ title_vi: "Dead air", fix_vi: "Xen cận." }];
    const out = peerTilesForGapAtIndex(0, gaps, tiles, "structure", true);
    expect(out[0].narrative_vi).not.toContain("Để xử lý «");
    expect(out[0].narrative_vi).not.toMatch(/^Thiếu sót «/);
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

  it("strips internal transcript marker from caption fallback", () => {
    const marker =
      "[Transcript không khả dụng — Gemini không nhận diện được tiếng Việt]";
    expect(
      referenceTileNarrative({
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: `${marker} Get ready with meee makeup`,
        posted_at: "",
      }),
    ).toContain("Get ready with meee makeup");
    expect(
      referenceTileNarrative({
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: `${marker} Get ready with meee makeup`,
        posted_at: "",
      }),
    ).not.toContain("Transcript không khả dụng");
  });

  it("strips internal transcript marker from cached narrative_vi", () => {
    const marker =
      "[Transcript không khả dụng — Gemini không nhận diện được tiếng Việt]";
    expect(
      referenceTileNarrative({
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "",
        posted_at: "",
        narrative_vi: `${marker} Peer mở text overlay sớm ở 0,4 giây đầu clip.`,
      }),
    ).not.toContain("Transcript không khả dụng");
    expect(
      referenceTileNarrative({
        video_url: "",
        thumbnail_url: "",
        views: 1,
        caption_snippet: "",
        posted_at: "",
        narrative_vi: `${marker} Peer mở text overlay sớm ở 0,4 giây đầu clip.`,
      }),
    ).toContain("Peer mở text overlay");
  });
});

describe("sanitizeReferenceCaptionSnippet", () => {
  it("removes transcript guard markers and collapses whitespace", () => {
    const out = sanitizeReferenceCaptionSnippet(
      "[Transcript không khả dụng] makeup   skincare",
    );
    expect(out).toBe("makeup skincare");
  });

  it("strips marker before truncation in mapDiagnosisEmbeddedTiles", () => {
    const marker =
      "[Transcript không khả dụng — Gemini không nhận diện được tiếng Việt]";
    const tail = "B".repeat(250);
    const tiles = mapDiagnosisEmbeddedTiles(
      [{ aweme_id: "111" }],
      [
        {
          aweme_id: "111",
          desc: `${marker} ${tail}`,
          hook_type: null,
          content_format: null,
          views: 1000,
          engagement_rate: null,
          author_handle: "@peer",
          thumbnail_url: "https://t/1.jpg",
          tiktok_url: "https://tiktok.com/@peer/video/111",
          source: "corpus",
        },
      ],
    );
    expect(tiles[0].caption_snippet).toBe(tail.slice(0, 200));
    expect(tiles[0].caption_snippet).not.toContain("Transcript không khả dụng");
  });
});

describe("formatNichePatternBridgeProse", () => {
  it("mentions format label when provided", () => {
    expect(formatNichePatternBridgeProse(2, "Đánh giá")).toContain("định dạng Đánh giá");
    expect(formatNichePatternBridgeProse(2, "Đánh giá")).toContain("2 clip dưới");
  });

  it("falls back to generic formula wording", () => {
    expect(formatNichePatternBridgeProse(1, null)).toContain("công thức đang chạy");
  });
});

describe("fallbackNichePatternReferenceTiles", () => {
  it("maps top reference videos by views", () => {
    const out = fallbackNichePatternReferenceTiles([
      {
        aweme_id: "1",
        desc: "A",
        hook_type: null,
        content_format: "review",
        views: 10_000,
        engagement_rate: null,
        author_handle: "@a",
        thumbnail_url: "https://t/1.jpg",
        tiktok_url: "https://tiktok.com/1",
        source: "corpus",
      },
      {
        aweme_id: "2",
        desc: "B",
        hook_type: null,
        content_format: "review",
        views: 500_000,
        engagement_rate: null,
        author_handle: "@b",
        thumbnail_url: "https://t/2.jpg",
        tiktok_url: "https://tiktok.com/2",
        source: "corpus",
      },
    ]);
    expect(out).toHaveLength(2);
    expect(out[0].aweme_id).toBe("2");
    expect(out[0].narrative_vi).toBeTruthy();
  });

  it("prefers peers with the same content_format as the analyzed clip", () => {
    const out = fallbackNichePatternReferenceTiles(
      [
        {
          aweme_id: "1",
          desc: "Vlog top",
          hook_type: null,
          content_format: "vlog",
          views: 900_000,
          engagement_rate: null,
          author_handle: "@v",
          thumbnail_url: "https://t/1.jpg",
          tiktok_url: "https://tiktok.com/1",
          source: "corpus",
        },
        {
          aweme_id: "2",
          desc: "Review peer",
          hook_type: null,
          content_format: "review",
          views: 50_000,
          engagement_rate: null,
          author_handle: "@r",
          thumbnail_url: "https://t/2.jpg",
          tiktok_url: "https://tiktok.com/2",
          source: "corpus",
        },
      ],
      3,
      "review",
    );
    expect(out).toHaveLength(1);
    expect(out[0].aweme_id).toBe("2");
  });
});

function corpusRef(id: string, views: number, format = "review"): ReferenceVideoCard {
  return {
    aweme_id: id,
    desc: `Clip ${id}`,
    hook_type: null,
    content_format: format,
    views,
    engagement_rate: null,
    author_handle: `@u${id}`,
    thumbnail_url: `https://thumb/${id}.jpg`,
    tiktok_url: `https://tiktok.com/${id}`,
    source: "corpus",
  };
}

describe("referenceHasVisibleThumbnail", () => {
  it("requires a non-empty thumbnail_url (mirrors Cloud Run ref picker)", () => {
    expect(
      referenceHasVisibleThumbnail({
        ...corpusRef("1", 100),
        thumbnail_url: "https://r2/thumbnails/1.webp",
      }),
    ).toBe(true);
    expect(
      referenceHasVisibleThumbnail({
        ...corpusRef("2", 100),
        thumbnail_url: null,
      }),
    ).toBe(false);
  });
});

describe("ReferenceTileAllocator", () => {
  it("prefers peers with thumbnail_url when rotating fallback picks", () => {
    const refs = [
      { ...corpusRef("1", 1_000_000), thumbnail_url: "https://r2/1.webp" },
      { ...corpusRef("2", 950_000), thumbnail_url: "https://r2/2.webp" },
      { ...corpusRef("3", 900_000), thumbnail_url: "https://r2/3.webp" },
      { ...corpusRef("4", 2_000_000), thumbnail_url: null },
      { ...corpusRef("5", 1_800_000), thumbnail_url: null },
    ];
    const allocator = new ReferenceTileAllocator(refs);
    const first = allocator.allocateFallback(3);
    const second = allocator.allocateFallback(2);
    expect(first.map((t) => t.aweme_id)).toEqual(["1", "2", "3"]);
    expect(second.map((t) => t.aweme_id)).toEqual(["4", "5"]);
  });

  it("rotates fallback peers across sections instead of repeating top-3", () => {
    const refs = [
      corpusRef("1", 1_000_000),
      corpusRef("2", 900_000),
      corpusRef("3", 800_000),
      corpusRef("4", 700_000),
      corpusRef("5", 600_000),
      corpusRef("6", 500_000),
    ];
    const allocator = new ReferenceTileAllocator(refs);
    const first = allocator.allocateFallback(3);
    const second = allocator.allocateFallback(3);
    const firstIds = first.map((t) => t.aweme_id);
    const secondIds = second.map((t) => t.aweme_id);
    expect(firstIds).toEqual(["1", "2", "3"]);
    expect(secondIds).toEqual(["4", "5", "6"]);
    for (const id of secondIds) {
      expect(firstIds).not.toContain(id);
    }
  });

  it("swaps duplicate synthesis tiles for unused corpus peers when possible", () => {
    const refs = [
      corpusRef("1", 1_000_000),
      corpusRef("2", 900_000),
      corpusRef("3", 800_000),
      corpusRef("4", 700_000),
    ];
    const allocator = new ReferenceTileAllocator(refs);
    const section = {
      section_id: "diagnosis",
      embedded_tiles: [{ aweme_id: "1" }, { aweme_id: "1" }, { aweme_id: "2" }],
      findings: [],
    };
    const tiles = allocator.allocateSectionTiles(section, undefined, 3, "review");
    const ids = tiles.map((t) => t.aweme_id);
    expect(ids).toHaveLength(3);
    expect(new Set(ids).size).toBe(3);
    expect(ids.filter((id) => id === "1")).toHaveLength(1);
  });
});

describe("sectionProseHasNichePatternBridge", () => {
  it("detects synthesis bridge and strip removes trailing duplicate", () => {
    const prose =
      "**Định dạng đánh giá** chiếm 35% view ngách. 3 clip dưới là video dẫn đầu ngách cùng công thức đánh giá.";
    expect(sectionProseHasNichePatternBridge(prose)).toBe(true);
    expect(stripSectionProseForEmbeddedRefs(prose)).toBe(
      "**Định dạng đánh giá** chiếm 35% view ngách.",
    );
  });
});
