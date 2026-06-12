import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import { ScriptBody } from "./ScriptBody";
import type { ScriptReportPayload } from "@/lib/api-types";
import { useSceneIntelligence } from "@/hooks/useSceneIntelligence";

vi.mock("@/hooks/useScriptSave", () => ({
  useScriptSave: () => ({ mutate: vi.fn(), isPending: false, data: null }),
  useScriptExport: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/components/v2/answer/script/ScriptExportModal", () => ({
  ScriptExportModal: () => null,
}));

vi.mock("@/hooks/useSceneIntelligence", () => ({
  useSceneIntelligence: vi.fn(() => ({ data: undefined })),
}));

afterEach(() => {
  cleanup();
  vi.mocked(useSceneIntelligence).mockReturnValue({ data: undefined } as unknown as ReturnType<
    typeof useSceneIntelligence
  >);
});

const sampleReport: ScriptReportPayload = {
  topic: "Review serum vitamin C",
  hook: "Đừng mua serum nếu chưa xem clip này",
  hook_delay_ms: 1000,
  duration: 32,
  tone: "Chuyên gia",
  niche_label: "Làm đẹp",
  narrative_vi: {
    headline_vi: "Serum C — hook cảnh báo + demo 3 bước",
    ket_luan_nhanh: "Cấu trúc 6 cảnh giữ retention bằng cận mặt và overlay số liệu.",
    _schema_version: "script_v1",
    diagnosis_vi: {
      headline_vi: "Serum C — hook cảnh báo + demo 3 bước",
      sections: [
        {
          section_id: "hook_analysis",
          title_vi: "Hook 0–3 giây",
          text_vi: "Mở bằng cảnh báo trực diện.",
        },
        {
          section_id: "script_structure",
          title_vi: "Cấu trúc 6 cảnh",
          text_vi: "Xen demo sản phẩm giữa 2 lần cận mặt.",
        },
        {
          section_id: "next_video",
          title_vi: "Video tiếp theo",
          text_vi: "Quay biến thể so sánh giá rẻ vs đắt cùng hook.",
        },
      ],
    },
  },
  shots: [
    {
      t0: 0,
      t1: 3,
      cam: "Cận mặt",
      voice: "Đừng mua serum nếu…",
      viz: "Cận mặt + text đỏ",
      overlay: "BOLD CENTER",
    },
  ],
  sources: [],
  related_questions: [],
};

function renderScriptBody(report: ScriptReportPayload = sampleReport, nicheId = 4) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ScriptBody report={report} nicheId={nicheId} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ScriptBody narrative IA", () => {
  it("renders verdict header and shot panel without legacy analysis wall", () => {
    renderScriptBody();
    expect(screen.getByText(/Serum C — hook cảnh báo/)).toBeTruthy();
    expect(screen.getByText(/Cấu trúc 6 cảnh giữ retention/)).toBeTruthy();
    expect(screen.getByText(/1 cảnh · hướng dẫn quay/)).toBeTruthy();
    expect(screen.getByText(/Cảnh 1 \/ 1/)).toBeTruthy();
    expect(screen.queryByText(/Phân tích kịch bản/)).toBeNull();
    expect(screen.queryByText(/Hook 0–3 giây/)).toBeNull();
    expect(screen.queryByText(/mảng 2\.4s/)).toBeNull();
  });

  it("surfaces next_video callout and deduped corpus strip", () => {
    renderScriptBody({
      ...sampleReport,
      narrative_vi: {
        ...sampleReport.narrative_vi!,
        ket_luan_nhanh:
          "Format này dựa trên @hi.vidayyy (27.461 view). Cấu trúc 6 cảnh giữ retention bằng cận mặt.",
      },
      shots: [
        {
          ...sampleReport.shots![0]!,
          references: [
            {
              video_id: "v-ref-1",
              scene_index: 0,
              thumbnail_url: "https://media.getviews.vn/thumbnails/v-ref-1.webp",
              tiktok_url: "https://www.tiktok.com/@creator/video/v-ref-1",
              creator_handle: "creator",
              description: "Cận mặt cảnh báo, text đỏ góc trên.",
              views: 256_000,
              match_label: "Cùng ngách, hook, khung hình",
            },
          ],
        },
      ],
    });

    const nextRegion = screen.getByRole("region", { name: "Video tiếp theo nên quay" });
    expect(within(nextRegion).getByText(/Quay biến thể so sánh giá rẻ vs đắt/)).toBeTruthy();
    expect(screen.getByRole("region", { name: "Clip tham chiếu từ corpus" })).toBeTruthy();
    const corpusRegion = screen.getByRole("region", { name: "Clip tham chiếu từ corpus" });
    expect(within(corpusRegion).getByText(/Cận mặt cảnh báo, text đỏ góc trên/)).toBeTruthy();
    expect(screen.getByText(/Cấu trúc 6 cảnh giữ retention bằng cận mặt/)).toBeTruthy();
    expect(screen.queryByText(/Format này dựa trên @hi\.vidayyy/i)).toBeNull();
  });

  it("renders scene intelligence panel when scene_type matches active shot", () => {
    vi.mocked(useSceneIntelligence).mockReturnValue({
      data: {
        niche_id: 4,
        scenes: [
          {
            niche_id: 4,
            scene_type: "face_to_camera",
            corpus_avg_duration: 2.8,
            winner_avg_duration: 2.4,
            winner_overlay_style: "white sans 28pt · bottom-center",
            overlay_samples: ["ĐỪNG MUA SERUM NÀY"],
            tip: "Hook cận mặt trong 3 giây — giữ khung ổn định.",
            reference_video_ids: [],
            sample_size: 45,
            computed_at: "2026-05-23T00:00:00Z",
          },
        ],
      },
    } as unknown as ReturnType<typeof useSceneIntelligence>);

    renderScriptBody({
      ...sampleReport,
      shots: [
        {
          ...sampleReport.shots![0]!,
          intel_scene_type: "face_to_camera",
        },
      ],
    });

    expect(screen.getByText(/Hook cận mặt trong 3 giây/)).toBeTruthy();
    expect(screen.getByText(/SHOT 01 · PHÂN TÍCH CẤU TRÚC/)).toBeTruthy();
  });
});
