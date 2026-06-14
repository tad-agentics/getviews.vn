import { afterEach, describe, expect, it, vi } from "vitest";

import {
  STRUCTURE_AXIS_TITLES,
  VIDEO_STRUCTURE_SECTION_TITLE,
  mergeVideoStructureSections,
} from "./mergeVideoStructureSections";
import * as presentationV2 from "./presentationV2";

describe("mergeVideoStructureSections", () => {
  it("merges sound + script_structure after hook_analysis with structure_axes", () => {
    const out = mergeVideoStructureSections([
      { section_id: "diagnosis", title_vi: "Chẩn đoán", text_vi: "D" },
      { section_id: "hook_analysis", title_vi: "Phân tích hook", text_vi: "H" },
      {
        section_id: "sound",
        title_vi: "Âm thanh và nhịp điệu",
        text_vi: "Voiceover mỏng.",
        findings: [{ title_vi: "Hook im lặng", fix_vi: "Mở bằng voiceover." }],
      },
      {
        section_id: "script_structure",
        title_vi: "Dòng thời gian · Cấu trúc video",
        text_vi: "Timeline prose.",
      },
      { section_id: "next_video", title_vi: "Gợi ý", text_vi: "N" },
    ]);

    expect(out.map((s) => s.section_id)).toEqual([
      "diagnosis",
      "hook_analysis",
      "script_structure",
      "next_video",
    ]);
    expect(out[2].title_vi).toBe(VIDEO_STRUCTURE_SECTION_TITLE);
    expect(out[2].findings).toHaveLength(1);
    expect(out[2].structure_axes?.map((a) => a.axis_id)).toEqual(["rhythm", "sound"]);
    expect(out[2].structure_axes?.[0]?.text_vi).toBe("Timeline prose.");
    expect(out[2].structure_axes?.[1]?.title_vi).toBe(STRUCTURE_AXIS_TITLES.sound);
    expect(out.find((s) => s.section_id === "sound")).toBeUndefined();
  });

  it("places merged block at end when hook_analysis is absent", () => {
    const out = mergeVideoStructureSections([
      { section_id: "diagnosis", title_vi: "Chẩn đoán" },
      { section_id: "sound", title_vi: "Âm thanh", text_vi: "S" },
    ]);
    expect(out.map((s) => s.section_id)).toEqual(["diagnosis", "script_structure"]);
    expect(out[1].structure_axes).toEqual([
      expect.objectContaining({ axis_id: "sound", text_vi: "S" }),
    ]);
  });

  it("returns input unchanged when no structure sources present", () => {
    const input = [
      { section_id: "diagnosis", title_vi: "Chẩn đoán" },
      { section_id: "hook_analysis", title_vi: "Hook" },
    ];
    expect(mergeVideoStructureSections(input)).toEqual(input);
  });

  it("merges persona-only into script_structure block", () => {
    const out = mergeVideoStructureSections([
      { section_id: "hook_analysis", title_vi: "Hook" },
      {
        section_id: "persona",
        title_vi: "Phong cách và nhân vật",
        text_vi: "Persona prose.",
        findings: [{ title_vi: "Thiếu tính chân thực", fix_vi: "Thêm chi tiết tiêu cực." }],
      },
    ]);
    expect(out.map((s) => s.section_id)).toEqual(["hook_analysis", "script_structure"]);
    expect(out[1].title_vi).toBe(VIDEO_STRUCTURE_SECTION_TITLE);
    expect(out[1].findings?.[0]?.title_vi).toBe("Thiếu tính chân thực");
    expect(out[1].structure_axes?.[0]?.axis_id).toBe("persona");
    expect(out.find((s) => s.section_id === "persona")).toBeUndefined();
  });

  it("keeps separate structure_axes for rhythm and persona prose", () => {
    const out = mergeVideoStructureSections([
      {
        section_id: "script_structure",
        text_vi: "Cấu trúc clip yếu nhịp cắt.",
      },
      {
        section_id: "persona",
        text_vi: "Giọng đọc thiếu va chạm trải nghiệm.",
      },
    ]);
    expect(out[0].structure_axes?.map((a) => a.axis_id)).toEqual(["rhythm", "persona"]);
    expect(out[0].structure_axes?.[0]?.text_vi).toBe("Cấu trúc clip yếu nhịp cắt.");
    expect(out[0].structure_axes?.[1]?.text_vi).toBe("Giọng đọc thiếu va chạm trải nghiệm.");
  });

  it("keeps rhythm and sound axes separate when both have text", () => {
    const out = mergeVideoStructureSections([
      { section_id: "sound", text_vi: "Sound prose riêng.", findings: [] },
      { section_id: "script_structure", text_vi: "Script prose nhịp cắt." },
    ]);
    expect(out[0].structure_axes?.map((a) => a.axis_id)).toEqual(["rhythm", "sound"]);
    expect(out[0].structure_axes?.[1]?.text_vi).toBe("Sound prose riêng.");
  });

  it("sound-only axis when script_structure text is empty", () => {
    const out = mergeVideoStructureSections([
      { section_id: "sound", text_vi: "Legacy sound prose." },
      { section_id: "script_structure", text_vi: "" },
    ]);
    expect(out[0].structure_axes).toEqual([
      expect.objectContaining({ axis_id: "sound", text_vi: "Legacy sound prose." }),
    ]);
  });

  it("dedupes embedded_tiles by aweme_id and prefers script_structure tiles", () => {
    const out = mergeVideoStructureSections([
      {
        section_id: "script_structure",
        embedded_tiles: [
          { aweme_id: "111", narrative_vi: "Script tile." },
          { aweme_id: "222", narrative_vi: "Script tile 2." },
        ],
      },
      {
        section_id: "sound",
        embedded_tiles: [
          { aweme_id: "111", narrative_vi: "Duplicate sound tile." },
          { aweme_id: "333", narrative_vi: "Sound tile." },
        ],
      },
    ]);
    const ids = (out[0].embedded_tiles ?? []).map((t) =>
      String((t as { aweme_id?: string }).aweme_id),
    );
    expect(ids).toEqual(["111", "222", "333"]);
  });

  it("merges editing into structure block and drops standalone editing section", () => {
    const out = mergeVideoStructureSections([
      { section_id: "hook_analysis", title_vi: "Hook" },
      {
        section_id: "editing",
        title_vi: "Màu sắc và chữ trên hình",
        text_vi: "Overlay mờ ở giữa clip.",
        findings: [{ title_vi: "Chữ nhỏ", fix_vi: "Tăng font overlay lên 48px." }],
      },
      {
        section_id: "script_structure",
        text_vi: "Nhịp cắt prose.",
      },
    ]);
    expect(out.map((s) => s.section_id)).toEqual(["hook_analysis", "script_structure"]);
    expect(out[1].structure_axes?.map((a) => a.axis_id)).toEqual(["rhythm", "editing"]);
    expect(out[1].structure_axes?.[1]?.title_vi).toBe(STRUCTURE_AXIS_TITLES.editing);
    expect(out.find((s) => s.section_id === "editing")).toBeUndefined();
  });

  it("merges commerce into structure block as cta axis", () => {
    const out = mergeVideoStructureSections([
      { section_id: "hook_analysis", title_vi: "Hook" },
      {
        section_id: "script_structure",
        text_vi: "Nhịp cắt prose.",
      },
      {
        section_id: "commerce",
        title_vi: "Kêu gọi hành động",
        text_vi: "Thiếu lời kêu mua cuối clip.",
        findings: [
          {
            title_vi: "Thiếu CTA bằng giọng",
            fix_vi: "Thêm câu cuối: 'Lưu lại để phối đồ theo nha'.",
          },
        ],
      },
    ]);
    expect(out.map((s) => s.section_id)).toEqual(["hook_analysis", "script_structure"]);
    expect(out[1].structure_axes?.map((a) => a.axis_id)).toEqual(["rhythm", "cta"]);
    expect(out[1].structure_axes?.[1]?.title_vi).toBe(STRUCTURE_AXIS_TITLES.cta);
    expect(out.find((s) => s.section_id === "commerce")).toBeUndefined();
  });

  it("round-robins findings so persona and sound are not dropped", () => {
    const out = mergeVideoStructureSections([
      {
        section_id: "script_structure",
        findings: [
          { title_vi: "S1", fix_vi: "Tiếp tục giữ nhịp." },
          { title_vi: "S2", fix_vi: "Sửa dead air." },
        ],
      },
      {
        section_id: "sound",
        findings: [
          { title_vi: "A1", fix_vi: "Thêm voiceover." },
          { title_vi: "A2", fix_vi: "Tăng nhạc nền." },
        ],
      },
      {
        section_id: "persona",
        findings: [{ title_vi: "P1", fix_vi: "Thêm trải nghiệm tiêu cực." }],
      },
    ]);
    expect(out[0].findings?.map((f) => f.title_vi)).toEqual(["S1", "A1", "P1", "S2", "A2"]);
  });

  describe("presentation v2 (A1b closing relocation)", () => {
    afterEach(() => vi.restoreAllMocks());

    it("moves script prose to block closing and clears rhythm text", () => {
      vi.spyOn(presentationV2, "isReportPresentationV2").mockReturnValue(true);
      const out = mergeVideoStructureSections([
        { section_id: "script_structure", text_vi: "Tóm lại nên dồn payoff sớm." },
        { section_id: "sound", text_vi: "Sound prose." },
      ]);
      // Block-level closing carries the script prose.
      expect(out[0].text_vi).toBe("Tóm lại nên dồn payoff sớm.");
      // Rhythm axis is dropped (no text/findings/tiles left); sound axis remains.
      expect(out[0].structure_axes?.map((a) => a.axis_id)).toEqual(["sound"]);
    });

    it("keeps rhythm axis when it still has findings", () => {
      vi.spyOn(presentationV2, "isReportPresentationV2").mockReturnValue(true);
      const out = mergeVideoStructureSections([
        {
          section_id: "script_structure",
          text_vi: "Closing.",
          findings: [{ title_vi: "Nhịp chậm", fix_vi: "Cắt nhanh hơn." }],
        },
      ]);
      expect(out[0].text_vi).toBe("Closing.");
      expect(out[0].structure_axes?.map((a) => a.axis_id)).toEqual(["rhythm"]);
      expect(out[0].structure_axes?.[0]?.text_vi).toBe("");
    });
  });
});
