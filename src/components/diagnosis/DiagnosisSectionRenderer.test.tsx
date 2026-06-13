/**
 * DiagnosisSectionRenderer — regressions from the 2026-06-12 live
 * video-diagnosis report audit:
 *   - keep-advice findings get a positive "Giữ" chip, not "Sửa",
 *   - section prose renders **bold** as <strong> (no literal ``**``).
 */
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { DiagnosisSectionVi } from "@/lib/api-types";
import { INFORMATIVE_STRUCTURE_SEGMENTS } from "@/lib/testFixtures/informativeStructureSegments";

import { DiagnosisSectionRenderer } from "./DiagnosisSectionRenderer";
import { humanizeStatsProse } from "@/lib/humanizeStatsProse";

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

describe("diagnosis strength-gap layout", () => {
  it("hit tier (Đang làm tốt) shows strengths without peer reference cards", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "diagnosis",
          title_vi: "Đang làm tốt",
          text_vi: "Video breakout.",
          findings: [
            {
              title_vi: "Hook mạnh",
              fix_vi: "Tiếp tục giữ hook câu hỏi.",
            },
          ],
          embedded_tiles: [{ aweme_id: "111", narrative_vi: "Peer hook mạnh hơn." }],
        }}
        referenceVideos={[
          {
            aweme_id: "111",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 100_000,
            engagement_rate: null,
            author_handle: "@peer",
            thumbnail_url: "https://t/1.jpg",
            tiktok_url: "https://tiktok.com/@peer/video/111",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.getByText("ĐIỂM MẠNH")).toBeTruthy();
    expect(screen.queryByText("KHOẢNG TRỐNG")).toBeNull();
    expect(container.querySelector("a[href*='tiktok.com']")).toBeNull();
  });

  it("renders strength/gap subsections, bridge prose, and gap-linked reference cards", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "diagnosis",
          title_vi: "Điểm mạnh và khoảng trống",
          text_vi:
            "**Hình mẫu trắc nghiệm** đang kéo view tốt. Sự kết hợp ASMR và trắc nghiệm tạo tò mò. Video vượt 1,8× mức view thường của kênh. Peer trong ngách mở hook cụ thể hơn.",
          findings: [
            {
              title_vi: "Nhịp ASMR ổn",
              body_vi: "Giữ chân ổn định.",
              fix_vi: "Tiếp tục dùng texture ASMR làm nền.",
            },
            {
              title_vi: "Hook thiếu điểm nhạy",
              body_vi: "Câu mở quá chung.",
              fix_vi: "Đổi thành câu hỏi cụ thể trong 0s.",
            },
          ],
          embedded_tiles: [
            {
              aweme_id: "111",
              narrative_vi:
                "Được chọn vì cấu trúc format và nhịp dẫn nhất quán suốt clip. So format và giữ chân suốt clip với video đang phân tích.",
            },
          ],
        }}
        referenceVideos={[
          {
            aweme_id: "111",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 100_000,
            engagement_rate: null,
            author_handle: "@peer",
            thumbnail_url: "https://t/1.jpg",
            tiktok_url: "https://tiktok.com/@peer/video/111",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.getByText("ĐIỂM MẠNH")).toBeTruthy();
    expect(screen.getByText("KHOẢNG TRỐNG")).toBeTruthy();
    expect(screen.getByText(/Để khắc phục «Hook thiếu điểm nhạy»/)).toBeTruthy();
    expect(screen.getByText(/Để xử lý «Hook thiếu điểm nhạy»/)).toBeTruthy();
    expect(screen.queryByText("Được chọn vì")).toBeNull();
    expect(container.querySelector("a[href*='tiktok.com']")).toBeTruthy();
  });
});

describe("video structure strength-gap layout", () => {
  it("renders four-axis layout with editing kicker and eight-beat timeline under rhythm", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "script_structure",
          title_vi: "Phân tích cấu trúc Video",
          structure_axes: [
            {
              axis_id: "rhythm",
              title_vi: "Nhịp & cắt",
              text_vi: "**Nhịp cắt 1,2s/cảnh** giữ chân ổn.",
              findings: [
                {
                  title_vi: "Nhịp cắt nhanh",
                  fix_vi: "Tiếp tục giữ nhịp cắt 1,2s/cảnh.",
                },
              ],
            },
            {
              axis_id: "editing",
              title_vi: "Hậu kỳ & hình",
              text_vi: "Chữ overlay mờ ở giữa clip.",
              findings: [{ title_vi: "Chữ nhỏ", fix_vi: "Tăng font overlay lên 48px." }],
            },
          ],
        }}
        referenceVideos={[]}
        videoEmbeds={{
          structureTimeline: {
            durationSec: 60,
            segments: INFORMATIVE_STRUCTURE_SEGMENTS,
          },
        }}
      />,
    );
    expect(screen.getByText("Hậu kỳ & hình")).toBeTruthy();
    expect(screen.getByLabelText("Dòng thời gian cấu trúc video")).toBeTruthy();
    expect(screen.getByText(/Hook kéo dài/)).toBeTruthy();
    expect(container.querySelectorAll('[aria-label="Dòng thời gian cấu trúc video"]')).toHaveLength(
      1,
    );
  });

  it("renders three-axis layout with per-axis kickers and gap-linked peers", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "script_structure",
          title_vi: "Phân tích cấu trúc Video",
          structure_axes: [
            {
              axis_id: "rhythm",
              title_vi: "Nhịp & cắt",
              text_vi:
                "**Nhịp cắt 1,2s/cảnh** giữ chân ổn nhưng dead air ở giữa làm rớt retention.",
              findings: [
                {
                  title_vi: "Nhịp cắt nhanh",
                  body_vi: "1,2s/cảnh — nhanh hơn median ngách.",
                  fix_vi: "Tiếp tục giữ nhịp cắt 1,2s/cảnh.",
                },
                {
                  title_vi: "Dead air giữa clip",
                  body_vi: "4s tĩnh ở 8-12s.",
                  fix_vi: "Xen cận hoặc text overlay mỗi 2s.",
                },
              ],
              embedded_tiles: [
                {
                  aweme_id: "222",
                  narrative_vi: "Xen cận sản phẩm mỗi 2s — không để cảnh tĩnh quá 1,5s.",
                },
              ],
            },
            {
              axis_id: "sound",
              title_vi: "Âm thanh",
              text_vi: "Voiceover rõ nhưng nhạc nền lấn át lời ở giữa clip.",
              findings: [
                {
                  title_vi: "Nhạc lấn lời",
                  fix_vi: "Hạ BGM 30% khi có lời thoại.",
                },
              ],
            },
          ],
        }}
        referenceVideos={[
          {
            aweme_id: "222",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 200_000,
            engagement_rate: null,
            author_handle: "@struct",
            thumbnail_url: "https://t/2.jpg",
            tiktok_url: "https://tiktok.com/@struct/video/222",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.getByText("Nhịp & cắt")).toBeTruthy();
    expect(screen.getByText("Âm thanh")).toBeTruthy();
    expect(screen.getAllByText("ĐIỂM MẠNH").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("THIẾU SÓT").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Thiếu sót «Dead air giữa clip»/)).toBeTruthy();
    expect(container.querySelector("a[href*='tiktok.com']")).toBeTruthy();
  });

  it("renders flat strength-gap layout when structure_axes absent (legacy cache)", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "script_structure",
          title_vi: "Phân tích cấu trúc Video",
          text_vi:
            "**Nhịp cắt 1,2s/cảnh** giữ chân ổn nhưng dead air ở giữa làm rớt retention. Âm ASMR đủ texture. Hai đoạn tĩnh liên tiếp 4s. Clip tham chiếu dưới minh họa cách xen cận đúng nhịp.",
          findings: [
            {
              title_vi: "Nhịp cắt nhanh",
              body_vi: "1,2s/cảnh — nhanh hơn median ngách.",
              fix_vi: "Tiếp tục giữ nhịp cắt 1,2s/cảnh.",
            },
            {
              title_vi: "Dead air giữa clip",
              body_vi: "4s tĩnh ở 8-12s.",
              fix_vi: "Xen cận hoặc text overlay mỗi 2s.",
            },
          ],
          embedded_tiles: [
            {
              aweme_id: "222",
              narrative_vi: "Xen cận sản phẩm mỗi 2s — không để cảnh tĩnh quá 1,5s.",
            },
          ],
        }}
        referenceVideos={[
          {
            aweme_id: "222",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 200_000,
            engagement_rate: null,
            author_handle: "@struct",
            thumbnail_url: "https://t/2.jpg",
            tiktok_url: "https://tiktok.com/@struct/video/222",
            source: "corpus",
          },
        ]}
        videoEmbeds={{
          structureTimeline: {
            durationSec: 60,
            segments: INFORMATIVE_STRUCTURE_SEGMENTS,
          },
        }}
      />,
    );
    expect(screen.getByText("ĐIỂM MẠNH")).toBeTruthy();
    expect(screen.getByText("THIẾU SÓT")).toBeTruthy();
    expect(screen.getByLabelText("Dòng thời gian cấu trúc video")).toBeTruthy();
    expect(screen.getByText(/Hook kéo dài/)).toBeTruthy();
    expect(screen.queryByText("KHOẢNG TRỐNG")).toBeNull();
    expect(screen.getByText(/Thiếu sót «Dead air giữa clip»/)).toBeTruthy();
    expect(container.querySelector("a[href*='tiktok.com']")).toBeTruthy();
  });

  it("renders adjunct script_structure fallback prose without segment timeline", () => {
    render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "script_structure",
          title_vi: "Phân tích cấu trúc Video",
          text: "",
          findings: [],
        }}
        referenceVideos={[]}
        fallbackProse="8 nhịp kịch bản trong 28 giây."
      />,
    );
    expect(screen.getByText(/8 nhịp kịch bản/)).toBeTruthy();
    expect(screen.queryByText("BẰNG CHỨNG TRONG CLIP")).toBeNull();
  });
});

describe("hook_analysis strength-gap layout (#1)", () => {
  it("splits hook findings into ĐIỂM MẠNH / THIẾU SÓT and links peers to gaps only", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "hook_analysis",
          title_vi: "Phân tích hook",
          text_vi: "**Hook ổn** nhưng text overlay vào trễ.",
          findings: [
            { title_vi: "Mặt vào sớm", fix_vi: "Tiếp tục cho mặt vào 0,3s." },
            { title_vi: "Overlay trễ", body_vi: "Text vào 3,2s.", fix_vi: "Đưa text overlay về 0,5s." },
          ],
          embedded_tiles: [{ aweme_id: "333", narrative_vi: "Peer mở text 0,4s." }],
        }}
        referenceVideos={[
          {
            aweme_id: "333",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 120_000,
            engagement_rate: null,
            author_handle: "@hook",
            thumbnail_url: "https://t/3.jpg",
            tiktok_url: "https://tiktok.com/@hook/video/333",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.getByText("ĐIỂM MẠNH")).toBeTruthy();
    expect(screen.getByText("THIẾU SÓT")).toBeTruthy();
    expect(screen.getByText(/Thiếu sót «Overlay trễ»/)).toBeTruthy();
    expect(screen.getByText(/So cắt, chữ overlay và hình mở với clip của bạn/)).toBeTruthy();
    expect(screen.queryByText(/Để xử lý «Overlay trễ»/)).toBeNull();
    // Peer card inline under the gap (one gap → one tile).
    expect(container.querySelectorAll("a[href*='tiktok.com']").length).toBe(1);
  });

  it("renders one inline reference tile per hook gap when two gaps exist", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "hook_analysis",
          title_vi: "Phân tích hook",
          text_vi: "**Hook đơn lớp** thiếu text overlay sớm và lời thoại mute-safe.",
          findings: [
            { title_vi: "Overlay trễ", fix_vi: "Đưa text overlay về 0,5s." },
            { title_vi: "Thiếu lời thoại", fix_vi: "Thêm voice-over mở đầu 0–2s." },
          ],
          embedded_tiles: [
            { aweme_id: "333", narrative_vi: "Peer mở text 0,4s." },
            { aweme_id: "444", narrative_vi: "Peer có voice-over ngay 0,2s." },
          ],
        }}
        referenceVideos={[
          {
            aweme_id: "333",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 120_000,
            engagement_rate: null,
            author_handle: "@hook",
            thumbnail_url: "https://t/3.jpg",
            tiktok_url: "https://tiktok.com/@hook/video/333",
            source: "corpus",
          },
          {
            aweme_id: "444",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 98_000,
            engagement_rate: null,
            author_handle: "@hook2",
            thumbnail_url: "https://t/4.jpg",
            tiktok_url: "https://tiktok.com/@hook2/video/444",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(container.querySelectorAll("a[href*='tiktok.com']").length).toBe(2);
    expect(screen.getAllByText(/Thiếu sót «/).length).toBe(2);
    expect(screen.queryByText(/Để xử lý «Overlay trễ»/)).toBeNull();
  });

  it("shows empty-state copy when a hook gap has no paired peer tile", () => {
    render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "hook_analysis",
          title_vi: "Phân tích hook",
          text_vi: "**Hook mỏng** cần thêm lớp text.",
          findings: [
            { title_vi: "Overlay trễ", fix_vi: "Đưa text overlay về 0,5s." },
            { title_vi: "Thiếu voice", fix_vi: "Thêm voice-over mở đầu 0–2s." },
          ],
          embedded_tiles: [{ aweme_id: "333", narrative_vi: "Peer mở text 0,4s." }],
        }}
        referenceVideos={[
          {
            aweme_id: "333",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 120_000,
            engagement_rate: null,
            author_handle: "@hook",
            thumbnail_url: "https://t/3.jpg",
            tiktok_url: "https://tiktok.com/@hook/video/333",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Chưa có clip tham chiếu trong ngách/)).toBeTruthy();
  });
});

describe("finding without fix_vi → QUAN SÁT, no peer (#2)", () => {
  it("routes a no-fix finding to observations and hides peer cards", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "diagnosis",
          title_vi: "Đang làm tốt",
          text_vi: "Video chạy tốt.",
          findings: [{ title_vi: "Quan sát trung tính", body_vi: "Không có hành động." }],
          embedded_tiles: [{ aweme_id: "444", narrative_vi: "Peer." }],
        }}
        referenceVideos={[
          {
            aweme_id: "444",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 90_000,
            engagement_rate: null,
            author_handle: "@obs",
            thumbnail_url: "https://t/4.jpg",
            tiktok_url: "https://tiktok.com/@obs/video/444",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.getByText("QUAN SÁT")).toBeTruthy();
    expect(screen.queryByText("KHOẢNG TRỐNG")).toBeNull();
    expect(container.querySelector("a[href*='tiktok.com']")).toBeNull();
  });
});

describe("per-finding analyzed-clip evidence button (#3)", () => {
  it("shows 'Xem ...' button for a strength with evidence_ref + clip url", () => {
    render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "diagnosis",
          title_vi: "Đang làm tốt",
          text_vi: "Video chạy tốt.",
          findings: [
            {
              title_vi: "Mặt vào sớm",
              fix_vi: "Tiếp tục cho mặt vào 0,3s.",
              evidence_ref: { start_sec: 0, end_sec: 3, label_vi: "mặt vào khung" },
            },
          ],
        }}
        referenceVideos={[]}
        videoEmbeds={{
          analyzedClip: { videoId: "999", clipUrl: "https://r2.test/videos/999.mp4", durationSec: 28 },
        }}
      />,
    );
    expect(screen.getByText(/Xem 0–3s trong clip · mặt vào khung/)).toBeTruthy();
  });

  it("hides the button when the analyzed clip url is missing", () => {
    render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "diagnosis",
          title_vi: "Đang làm tốt",
          text_vi: "Video chạy tốt.",
          findings: [
            {
              title_vi: "Mặt vào sớm",
              fix_vi: "Tiếp tục cho mặt vào 0,3s.",
              evidence_ref: { start_sec: 0, end_sec: 3 },
            },
          ],
        }}
        referenceVideos={[]}
        videoEmbeds={{
          analyzedClip: { videoId: "999", clipUrl: null, durationSec: 28 },
        }}
      />,
    );
    expect(screen.queryByText(/Xem .* trong clip/)).toBeNull();
  });
});

describe("section verdict prose", () => {
  it("merges verdict + support into one paragraph when both are present", () => {
    const verdict =
      "Video đạt hiệu suất 3,06x so với mức view thường của kênh nhờ nhịp cắt nhanh, nhưng đang thiếu kết nối Người kể chuyện.";
    const support =
      "Việc không có tiếng nói trực tiếp khiến nội dung review mất đi 35% tiềm năng giữ chân.";
    const { container } = renderSection({
      section_id: "diagnosis",
      title: "Chẩn đoán",
      text: `${verdict}\n\n${support}`,
      findings: [],
    } as DiagnosisSectionVi);
    const humanizedSupport = humanizeStatsProse(support);
    const paragraphs = container.querySelectorAll("p");
    const merged = Array.from(paragraphs).find(
      (p) => p.textContent?.includes(verdict) && p.textContent?.includes(humanizedSupport),
    );
    expect(merged).toBeTruthy();
    expect(merged?.querySelector("span.font-bold")?.textContent).toBe(verdict);
  });
});

describe("section prose markdown", () => {
  it("renders **bold** as <strong> instead of literal asterisks", () => {
    const { container } = renderSection({
      section_id: "diagnosis",
      title: "Vấn đề chính",
      text: "**Quy trình đóng hộp** — giữ texture cận.",
      findings: [],
    } as DiagnosisSectionVi);
    expect(container.textContent).not.toContain("**");
    const bold = container.querySelector("span.font-bold");
    expect(bold?.textContent).toBe("Quy trình đóng hộp");
  });
});

describe("niche_pattern reference grid", () => {
  it("falls back to corpus peers and shows bridge prose when tiles missing", () => {
    const { container } = render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "niche_pattern",
          title_vi: "Công thức đang chạy trong ngách",
          text_vi:
            "**Định dạng đánh giá** chiếm 35% view ngách. Video này bám công thức thử thách mua sắm.",
          findings: [],
        }}
        referenceVideos={[
          {
            aweme_id: "999",
            desc: "Peer top",
            hook_type: "question",
            content_format: "review",
            views: 800_000,
            engagement_rate: null,
            author_handle: "@peer",
            thumbnail_url: "https://t/9.jpg",
            tiktok_url: "https://tiktok.com/999",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Clip dưới là video dẫn đầu ngách/)).toBeTruthy();
    expect(screen.queryByText("VIDEO DẪN ĐẦU NGÁCH")).toBeNull();
    expect(container.querySelector("a[href*='tiktok.com']")).toBeTruthy();
  });

  it("does not duplicate bridge when synthesis prose already leads into refs", () => {
    render(
      <DiagnosisSectionRenderer
        section={{
          section_id: "niche_pattern",
          title_vi: "Công thức đang chạy trong ngách",
          text_vi:
            "**Định dạng đánh giá** chiếm 35% view ngách. 2 clip dưới là video dẫn đầu ngách cùng công thức.",
          findings: [],
        }}
        analyzedContentFormat="review"
        referenceVideos={[
          {
            aweme_id: "999",
            desc: "Peer",
            hook_type: null,
            content_format: "review",
            views: 800_000,
            engagement_rate: null,
            author_handle: "@peer",
            thumbnail_url: "https://t/9.jpg",
            tiktok_url: "https://tiktok.com/999",
            source: "corpus",
          },
        ]}
      />,
    );
    expect(screen.queryByText(/Clip dưới là video dẫn đầu ngách/)).toBeNull();
    expect(screen.getByText(/2 clip dưới là video dẫn đầu ngách/)).toBeTruthy();
  });
});
