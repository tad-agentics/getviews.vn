import { describe, expect, it } from "vitest";

import {
  scriptNarrativeSectionTitle,
  scriptRefToDiagnosisTile,
  scriptSectionReferenceTiles,
} from "@/lib/scriptNarrativeRefs";
import type { DiagnosisSectionVi, ScriptShotCardData } from "@/lib/api-types";

describe("scriptNarrativeRefs", () => {
  it("maps hook_analysis to stable title", () => {
    expect(
      scriptNarrativeSectionTitle({
        section_id: "hook_analysis",
        title_vi: "Phân tích hook 0-3 giây",
        text_vi: "x",
      } as DiagnosisSectionVi),
    ).toBe("Hook 0–3 giây");
  });

  it("builds tiles for hook from shot 1 references", () => {
    const shots: ScriptShotCardData[] = [
      {
        references: [
          {
            video_id: "v1",
            creator_handle: "hi.vidayyy",
            views: 27_461,
            thumbnail_url: "https://media.getviews.vn/thumbnails/v1.webp",
            description: "Cận mặt hook",
          },
        ],
      },
      { references: [{ video_id: "v2", creator_handle: "other" }] },
    ];
    const tiles = scriptSectionReferenceTiles("hook_analysis", shots);
    expect(tiles).toHaveLength(1);
    expect(tiles[0]?.aweme_id).toBe("v1");
    expect(tiles[0]?.author_handle).toBe("hi.vidayyy");
  });

  it("scriptRefToDiagnosisTile builds tiktok url from handle", () => {
    const tile = scriptRefToDiagnosisTile({
      video_id: "999",
      creator_handle: "@creator",
      views: 100_000,
    });
    expect(tile?.video_url).toBe("https://www.tiktok.com/@creator/video/999");
  });
});
