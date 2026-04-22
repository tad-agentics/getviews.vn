/**
 * DiagnosticBody — render + verdict/fix contract regression.
 *
 * The backend ships 4 verdict variants + an invariant that
 * ``probably_fine`` categories never carry a fix_preview. These tests
 * pin the "which verdict renders what" contract so a schema drift
 * can't silently mis-render.
 */
import React from "react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach } from "vitest";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
  },
}));

import type {
  DiagnosticCategoryData,
  DiagnosticPrescriptionData,
  DiagnosticReportPayload,
  DiagnosticVerdictData,
} from "@/lib/api-types";
import { DiagnosticBody } from "./DiagnosticBody";

afterEach(cleanup);

const CATEGORY_NAMES = [
  "Hook (0–3s)",
  "Pacing (3–20s)",
  "CTA",
  "Sound",
  "Caption & Hashtag",
] as const;

// ── Payload factories ─────────────────────────────────────────────────────

function mkCategory(
  overrides: Partial<DiagnosticCategoryData> = {},
): DiagnosticCategoryData {
  return {
    name: "Hook (0–3s)",
    verdict: "unclear",
    finding: "stub finding",
    fix_preview: null,
    ...overrides,
  };
}

function mkFiveCategories(
  overrides?: Partial<DiagnosticCategoryData>[],
): DiagnosticCategoryData[] {
  return CATEGORY_NAMES.map((name, i) =>
    mkCategory({ name, ...(overrides?.[i] ?? {}) }),
  );
}

function mkReport(
  overrides: Partial<DiagnosticReportPayload> = {},
): DiagnosticReportPayload {
  return {
    confidence: {
      sample_size: 200,
      window_days: 14,
      niche_scope: "Skincare",
      freshness_hours: 6,
      intent_confidence: "medium",
      what_stalled_reason: null,
    },
    framing: "Chưa có link video — chẩn đoán dựa trên mô tả + benchmark ngách.",
    categories: mkFiveCategories(),
    prescriptions: [
      {
        priority: "P1",
        action: "Dán link video vào /app/video",
        impact: "Chẩn đoán chính xác hơn",
        effort: "low",
      },
    ],
    paste_link_cta: {
      title: "Có link video? Mở /app/video để chấm điểm chính xác.",
      route: "/app/video",
    },
    sources: [],
    related_questions: [],
    ...overrides,
  };
}

function renderBody(report: DiagnosticReportPayload) {
  return render(
    <MemoryRouter>
      <DiagnosticBody report={report} />
    </MemoryRouter>,
  );
}

// ── Verdict badge labels ──────────────────────────────────────────────────

describe("DiagnosticBody verdict badges", () => {
  it("renders VN labels for each of the 4 verdicts, not raw enum", () => {
    const verdicts: DiagnosticVerdictData[] = [
      "likely_issue",
      "possible_issue",
      "unclear",
      "probably_fine",
    ];
    const cats = CATEGORY_NAMES.map((name, i) =>
      mkCategory({ name, verdict: verdicts[i] ?? "unclear" }),
    );
    // 5th cell stays unclear (already set by default).
    renderBody(mkReport({ categories: cats }));

    expect(screen.getByText("Nhiều khả năng lỗi")).toBeTruthy();
    expect(screen.getByText("Có thể có lỗi")).toBeTruthy();
    expect(screen.getAllByText("Chưa đủ thông tin").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Có vẻ ổn")).toBeTruthy();

    // Raw enum values must never leak.
    expect(screen.queryByText("likely_issue")).toBeNull();
    expect(screen.queryByText("probably_fine")).toBeNull();
  });

  it("emits data-verdict attribute on each badge so tone tests are stable", () => {
    const cats = mkFiveCategories([
      { verdict: "likely_issue" },
      { verdict: "possible_issue" },
      { verdict: "unclear" },
      { verdict: "unclear" },
      { verdict: "probably_fine" },
    ]);
    const { container } = renderBody(mkReport({ categories: cats }));
    const verdictAttrs = Array.from(
      container.querySelectorAll("[data-verdict]"),
    ).map((el) => el.getAttribute("data-verdict"));
    expect(verdictAttrs).toEqual([
      "likely_issue",
      "possible_issue",
      "unclear",
      "unclear",
      "probably_fine",
    ]);
  });
});

// ── Framing + header ──────────────────────────────────────────────────────

describe("DiagnosticBody header", () => {
  it("renders the framing sentence directly (no template prefix)", () => {
    renderBody(
      mkReport({
        framing:
          "Chưa có link video — mình chẩn đoán dựa trên 'pacing chậm' và benchmark Skincare.",
      }),
    );
    expect(
      screen.getByText(
        /Chưa có link video — mình chẩn đoán dựa trên 'pacing chậm' và benchmark Skincare\./,
      ),
    ).toBeTruthy();
  });

  it("surfaces the 'Chẩn đoán URL-less' kicker", () => {
    renderBody(mkReport());
    expect(screen.getByText("Chẩn đoán URL-less")).toBeTruthy();
  });
});

// ── Category cards ────────────────────────────────────────────────────────

describe("DiagnosticBody category cards", () => {
  it("renders all 5 categories in pinned order", () => {
    renderBody(mkReport());
    for (const name of CATEGORY_NAMES) {
      expect(screen.getByText(name)).toBeTruthy();
    }
  });

  it("shows fix_preview when present (non-probably_fine)", () => {
    const cats = mkFiveCategories([
      { verdict: "likely_issue", fix_preview: "Rút hook ≤ 1.2 giây." },
    ]);
    renderBody(mkReport({ categories: cats }));
    expect(screen.getByText("Rút hook ≤ 1.2 giây.")).toBeTruthy();
  });

  it("hides fix_preview row when null (unclear case)", () => {
    renderBody(
      mkReport({
        categories: mkFiveCategories([
          { verdict: "unclear", fix_preview: null },
        ]),
      }),
    );
    // No fix text should render for the first category.
    expect(screen.queryByText(/Rút hook/)).toBeNull();
  });
});

// ── Prescription cards ────────────────────────────────────────────────────

describe("DiagnosticBody prescriptions", () => {
  it("renders priority + effort labels ('15 phút' / '30 phút' / '1 giờ')", () => {
    const ps: DiagnosticPrescriptionData[] = [
      {
        priority: "P1",
        action: "Viết lại hook.",
        impact: "+12-18% retention.",
        effort: "low",
      },
      {
        priority: "P2",
        action: "Tăng pacing.",
        impact: "-8% drop-off.",
        effort: "medium",
      },
      {
        priority: "P3",
        action: "Đổi audio.",
        impact: "+ discovery reach.",
        effort: "high",
      },
    ];
    renderBody(mkReport({ prescriptions: ps }));

    expect(screen.getByText("P1")).toBeTruthy();
    expect(screen.getByText("P2")).toBeTruthy();
    expect(screen.getByText("P3")).toBeTruthy();
    expect(screen.getByText("15 phút")).toBeTruthy();
    expect(screen.getByText("30 phút")).toBeTruthy();
    expect(screen.getByText("1 giờ")).toBeTruthy();
  });

  it("renders impact chip for each prescription", () => {
    const ps: DiagnosticPrescriptionData[] = [
      {
        priority: "P1",
        action: "Viết lại hook.",
        impact: "Dự báo: +12–18 điểm retention.",
        effort: "low",
      },
    ];
    renderBody(mkReport({ prescriptions: ps }));
    expect(screen.getByText("Dự báo: +12–18 điểm retention.")).toBeTruthy();
  });
});

// ── Paste-link CTA ────────────────────────────────────────────────────────

describe("DiagnosticBody paste-link CTA", () => {
  it("always renders the paste-link CTA block", () => {
    renderBody(mkReport());
    expect(screen.getByText("Chẩn đoán chính xác")).toBeTruthy();
    expect(
      screen.getByText(
        /Có link video\? Mở \/app\/video để chấm điểm chính xác\./,
      ),
    ).toBeTruthy();
  });
});

// ── Thin-sample banner ────────────────────────────────────────────────────

describe("DiagnosticBody thin-sample chip", () => {
  it("shows MẪU MỎNG when sample_size < 80", () => {
    renderBody(
      mkReport({
        confidence: {
          sample_size: 20,
          window_days: 14,
          niche_scope: "Skincare",
          freshness_hours: 6,
          intent_confidence: "low",
          what_stalled_reason: null,
        },
      }),
    );
    expect(screen.getByText("MẪU MỎNG")).toBeTruthy();
  });

  it("hides the chip when sample_size >= 80", () => {
    renderBody(
      mkReport({
        confidence: {
          sample_size: 200,
          window_days: 14,
          niche_scope: "Skincare",
          freshness_hours: 6,
          intent_confidence: "medium",
          what_stalled_reason: null,
        },
      }),
    );
    expect(screen.queryByText("MẪU MỎNG")).toBeNull();
  });
});
