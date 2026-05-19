import { describe, expect, it } from "vitest";

import { resolveDiagnosisSections } from "./resolveDiagnosisSections";

describe("resolveDiagnosisSections", () => {
  it("returns v6 sections when present", () => {
    const sections = resolveDiagnosisSections(
      {
        headline_vi: "H",
        ket_luan_nhanh: "",
        van_de_chinh: "legacy",
        loi_chinh_narrative: [],
        dinh_huong_chien_luoc: "",
        lessons: [],
        diagnosis_vi: {
          headline_vi: "H",
          sections: [{ section_id: "diagnosis", title_vi: "V6", text_vi: "from v6" }],
        },
      },
      [],
      "flop",
    );
    expect(sections).toHaveLength(1);
    expect(sections[0]?.text_vi).toBe("from v6");
  });

  it("shims legacy van_de_chinh and flop issues into one diagnosis section", () => {
    const sections = resolveDiagnosisSections(
      {
        headline_vi: "H",
        ket_luan_nhanh: "Kết luận nhanh.",
        van_de_chinh: "Vấn đề cốt lõi prose.",
        loi_chinh_narrative: [],
        dinh_huong_chien_luoc: "",
        lessons: [],
      },
      [
        {
          error_id: "e1",
          title: "Hook yếu",
          detail: "Chi tiết",
          fix: "Sửa hook",
          sev: "high",
          t: 0,
          end: 2,
        },
      ],
      "flop",
    );
    expect(sections[0]?.section_id).toBe("diagnosis");
    expect(sections[0]?.text_vi).toContain("Kết luận nhanh");
    expect(sections[0]?.text_vi).toContain("Vấn đề cốt lõi");
    expect(sections[0]?.findings).toHaveLength(1);
    expect(sections[0]?.findings?.[0]?.title_vi).toBe("Hook yếu");
  });
});
