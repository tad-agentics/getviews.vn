import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: { VITE_R2_PUBLIC_URL: "https://media.getviews.vn" },
}));

import { scriptRefToDiagnosisTile, scriptNextVideoText } from "@/lib/scriptNarrativeRefs";
import type { DiagnosisSectionVi } from "@/lib/api-types";

describe("scriptNarrativeRefs", () => {
  it("scriptRefToDiagnosisTile builds tiktok url and R2 playback", () => {
    const tile = scriptRefToDiagnosisTile({
      video_id: "999",
      creator_handle: "@creator",
      views: 100_000,
    });
    expect(tile?.video_url).toBe("https://www.tiktok.com/@creator/video/999");
    expect(tile?.playback_url).toMatch(/\/videos\/999\.mp4$/);
  });

  it("scriptNextVideoText returns next_video section only", () => {
    expect(
      scriptNextVideoText([
        { section_id: "hook_analysis", text_vi: "hook" } as DiagnosisSectionVi,
        { section_id: "next_video", text_vi: "Quay biến thể POV" } as DiagnosisSectionVi,
      ]),
    ).toBe("Quay biến thể POV");
  });
});
