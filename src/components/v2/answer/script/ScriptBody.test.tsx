import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ScriptBody } from "./ScriptBody";
import type { ScriptReportPayload } from "@/lib/api-types";

vi.mock("@/hooks/useScriptSave", () => ({
  useScriptSave: () => ({ mutate: vi.fn(), isPending: false, data: null }),
  useScriptExport: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/components/v2/answer/script/ScriptExportModal", () => ({
  ScriptExportModal: () => null,
}));

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
          text_vi: "Mở bằng cảnh báo trực diện — khớp top video skincare tuần qua.",
        },
        {
          section_id: "script_structure",
          title_vi: "Cấu trúc 6 cảnh",
          text_vi: "Xen demo sản phẩm giữa 2 lần cận mặt để tránh monoton.",
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

describe("ScriptBody narrative-first", () => {
  it("renders narrative headline before shot rail", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <ScriptBody report={sampleReport} />
      </QueryClientProvider>,
    );
    expect(screen.getByText(/Serum C — hook cảnh báo/)).toBeTruthy();
    expect(screen.getByText(/Hook 0–3 giây/)).toBeTruthy();
    expect(screen.getByText(/Cảnh 1 \/ 1/)).toBeTruthy();
  });
});
