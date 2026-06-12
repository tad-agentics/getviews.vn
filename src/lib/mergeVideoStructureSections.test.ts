import { describe, expect, it } from "vitest";

import {
  VIDEO_STRUCTURE_SECTION_TITLE,
  mergeVideoStructureSections,
} from "./mergeVideoStructureSections";

describe("mergeVideoStructureSections", () => {
  it("merges sound + script_structure after hook_analysis", () => {
    const out = mergeVideoStructureSections([
      { section_id: "diagnosis", title_vi: "Chẩn đoán", text_vi: "D" },
      { section_id: "hook_analysis", title_vi: "Phân tích hook", text_vi: "H" },
      {
        section_id: "sound",
        title_vi: "Âm thanh và nhịp điệu",
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
    expect(out[2].text_vi).toBe("Timeline prose.");
    expect(out.find((s) => s.section_id === "sound")).toBeUndefined();
  });

  it("places merged block at end when hook_analysis is absent", () => {
    const out = mergeVideoStructureSections([
      { section_id: "diagnosis", title_vi: "Chẩn đoán" },
      { section_id: "sound", title_vi: "Âm thanh", text_vi: "S" },
    ]);
    expect(out.map((s) => s.section_id)).toEqual(["diagnosis", "script_structure"]);
    expect(out[1].text_vi).toBe("S");
  });

  it("returns input unchanged when neither sound nor script_structure present", () => {
    const input = [
      { section_id: "diagnosis", title_vi: "Chẩn đoán" },
      { section_id: "hook_analysis", title_vi: "Hook" },
    ];
    expect(mergeVideoStructureSections(input)).toEqual(input);
  });

  it("keeps script_structure prose only when both sections have text", () => {
    const out = mergeVideoStructureSections([
      { section_id: "sound", text_vi: "Sound prose bị bỏ.", findings: [] },
      { section_id: "script_structure", text_vi: "Script prose giữ lại." },
    ]);
    expect(out[0].text_vi).toBe("Script prose giữ lại.");
    expect(out[0].text_vi).not.toContain("Sound prose");
  });

  it("falls back to sound prose when script_structure text is empty", () => {
    const out = mergeVideoStructureSections([
      { section_id: "sound", text_vi: "Legacy sound prose." },
      { section_id: "script_structure", text_vi: "" },
    ]);
    expect(out[0].text_vi).toBe("Legacy sound prose.");
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

  it("caps merged findings at three with script_structure first", () => {
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
    ]);
    expect(out[0].findings?.map((f) => f.title_vi)).toEqual(["S1", "S2", "A1"]);
  });
});
