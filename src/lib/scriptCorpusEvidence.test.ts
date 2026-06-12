import { describe, expect, it } from "vitest";

import { allScriptCorpusTiles } from "@/lib/scriptCorpusEvidence";
import type { ScriptShotCardData } from "@/lib/api-types";

describe("allScriptCorpusTiles", () => {
  it("dedupes references across shots", () => {
    const shots: ScriptShotCardData[] = [
      {
        references: [
          { video_id: "v1", creator_handle: "a", views: 10_000, description: "Hook" },
        ],
      },
      {
        references: [
          { video_id: "v1", creator_handle: "a", views: 10_000, description: "Hook" },
          { video_id: "v2", creator_handle: "b", views: 20_000, description: "Demo" },
        ],
      },
    ];
    const tiles = allScriptCorpusTiles(shots);
    expect(tiles).toHaveLength(2);
    expect(tiles.map((t) => t.aweme_id)).toEqual(["v1", "v2"]);
  });
});
