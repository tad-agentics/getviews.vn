/**
 * DiagnosisSectionRenderer — regressions from the 2026-06-12 live
 * video-diagnosis report audit:
 *   - keep-advice findings get a positive "Giữ" chip, not "Sửa",
 *   - next_video section text renders **bold** as <strong> (no literal ``**``),
 *   - next_video shot-script bullets render in chronological order,
 *   - the fabricated v6 next_video concept never shows "gap 0%"/"Peer TB ~0".
 */
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { DiagnosisSectionVi } from "@/lib/api-types";

import { DiagnosisSectionRenderer } from "./DiagnosisSectionRenderer";

afterEach(cleanup);

function renderSection(section: DiagnosisSectionVi) {
  return render(
    <DiagnosisSectionRenderer section={section} referenceVideos={[]} />,
  );
}

describe("SectionFindingCard fix chip", () => {
  it("renders 'Giữ' for keep-advice fixes", () => {
    renderSection({
      section_id: "diagnosis",
      title: "Chẩn đoán",
      text: "",
      findings: [
        {
          title_vi: "Nhịp cắt đang chạy tốt",
          body_vi: "1.2s/cảnh — nhanh hơn median ngách.",
          fix_vi: "Tiếp tục sử dụng nhịp cắt 1.2s/cảnh cho video tới.",
        },
      ],
    } as DiagnosisSectionVi);
    expect(screen.getByText("Giữ")).toBeTruthy();
    expect(screen.queryByText("Sửa")).toBeNull();
  });

  it("renders 'Sửa' for corrective fixes", () => {
    renderSection({
      section_id: "diagnosis",
      title: "Chẩn đoán",
      text: "",
      findings: [
        {
          title_vi: "Hook chậm",
          body_vi: "3 giây đầu là cảnh tĩnh.",
          fix_vi: "Mở bằng chuyển động + 1 câu hỏi trong 1s đầu.",
        },
      ],
    } as DiagnosisSectionVi);
    expect(screen.getByText("Sửa")).toBeTruthy();
    expect(screen.queryByText("Giữ")).toBeNull();
  });
});

describe("section verdict prose", () => {
  it("merges verdict + support into one paragraph when both are present", () => {
    const verdict =
      "Video đạt hiệu suất 3,06x so với mức view thường của kênh nhờ nhịp cắt nhanh, nhưng đang thiếu kết nối Người kể chuyện.";
    const support =
      "Việc không có tiếng nói trực tiếp khiến nội dung tutorial mất đi 35% tiềm năng giữ chân.";
    const { container } = renderSection({
      section_id: "diagnosis",
      title: "Chẩn đoán",
      text: `${verdict}\n\n${support}`,
      findings: [],
    } as DiagnosisSectionVi);
    const paragraphs = container.querySelectorAll("p");
    const merged = Array.from(paragraphs).find(
      (p) => p.textContent?.includes(verdict) && p.textContent?.includes(support),
    );
    expect(merged).toBeTruthy();
    expect(merged?.querySelector("span.font-bold")?.textContent).toBe(verdict);
  });
});

describe("section prose markdown", () => {
  it("renders **bold** as <strong> instead of literal asterisks", () => {
    const { container } = renderSection({
      section_id: "next_video",
      title: "Video tiếp theo nên quay",
      text: "Học nhịp video **Quy trình đóng hộp** — giữ texture cận.",
      findings: [],
    } as DiagnosisSectionVi);
    expect(container.textContent).not.toContain("**");
    const strong = container.querySelector("strong");
    expect(strong?.textContent).toBe("Quy trình đóng hộp");
  });
});

describe("next_video shot script", () => {
  it("sorts timestamped bullets chronologically (belt-and-braces)", () => {
    const { container } = renderSection({
      section_id: "next_video",
      title: "Video tiếp theo nên quay",
      text: [
        "• Beat 2 (8-12s): so sánh trước/sau",
        "• Hook (0-1s): câu hỏi đảo",
        "• Beat 1 (1-8s): demo cận",
        "• CTA: comment 'giá'",
      ].join("\n"),
      findings: [],
    } as DiagnosisSectionVi);
    const items = Array.from(container.querySelectorAll("li")).map(
      (li) => li.textContent ?? "",
    );
    expect(items[0]).toContain("Hook (0-1s)");
    expect(items[1]).toContain("Beat 1 (1-8s)");
    expect(items[2]).toContain("Beat 2 (8-12s)");
    expect(items[3]).toContain("CTA");
  });

  it("never renders 'gap 0%' / 'Peer TB ~0' from a loose v6 concept", () => {
    const { container } = renderSection({
      section_id: "next_video",
      title: "Video tiếp theo nên quay",
      text: "",
      findings: [],
      next_video: {
        hook_vi: "Mở bằng câu hỏi đảo.",
        premise_vi: "So sánh 2 sản phẩm cùng giá.",
        format: "talking_head",
        reason_vi: "Giữ giọng đọc; đổi cảnh mở.",
        expected_views_range: "25K - 40K",
      },
    } as unknown as DiagnosisSectionVi);
    expect(container.textContent).not.toContain("gap");
    expect(container.textContent).not.toContain("Peer TB");
    expect(container.textContent).not.toContain("format trên kênh");
  });
});
