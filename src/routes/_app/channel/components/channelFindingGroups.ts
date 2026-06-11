import type { ChannelDiagnosisFinding } from "@/lib/api-types";

/** V5 audit rings — map finding_id → audit step (channel roll-up). */
export const ACCOUNT_HEALTH_FINDING_IDS = new Set([
  "channel_view_ceiling_300",
  "channel_boost_outlier_share",
]);

export const VONG2_FINDING_IDS = new Set([
  "channel_format_entropy_high",
  "channel_persona_drift",
  "channel_posting_cadence_vs_peer",
]);

/** Vòng 0 — pre-publish / compliance gates (V5 §2 Vòng 0). */
export const VONG0_PREFLIGHT_FINDING_IDS = new Set([
  "channel_compliance_aggregate",
  "channel_restricted_keyword_exposure",
  "channel_ad_law_disclosure_gap",
  "channel_copyright_mute_risk",
]);

/** Vòng 3 — peer format saturation / breakout ceiling (channel proxy). */
export const VONG3_VIRAL_FINDING_IDS = new Set(["channel_peer_format_saturation"]);

/** Vòng 4 — audience, seasonality, slang (V5 §2 tail). */
export const VONG4_AUDIENCE_FINDING_IDS = new Set([
  "channel_recent_vs_peak_er_drop",
  "channel_mega_sale_dip",
  "channel_slang_staleness",
]);

/** @deprecated Renamed — use ``VONG0_PREFLIGHT_FINDING_IDS``. */
export const VONG3_FINDING_IDS = VONG0_PREFLIGHT_FINDING_IDS;

/** @deprecated Split into ``VONG3_VIRAL`` + ``VONG4_AUDIENCE``. */
export const VONG4_FINDING_IDS = new Set([
  ...VONG3_VIRAL_FINDING_IDS,
  ...VONG4_AUDIENCE_FINDING_IDS,
]);

export const POLICY_RISK_FINDING_IDS = new Set([...VONG0_PREFLIGHT_FINDING_IDS]);

export type AuditRingId = "v0" | "v1" | "v2" | "v3" | "v4";

export type AuditRingDef = {
  id: AuditRingId;
  step: number;
  title: string;
  subtitle: string;
  hint: string;
  findingIds: Set<string>;
};

/** Five-ring audit map — V5-inspired KPI copy, channel finding IDs. */
export const AUDIT_RINGS: readonly AuditRingDef[] = [
  {
    id: "v0",
    step: 0,
    title: "Vòng 0 — Trước khi đăng",
    subtitle: "Điều kiện phân phối · nhãn quảng cáo · nhạc nền · chữ trên video",
    hint: "Kiểm tra mô tả & lời thoại — gắn nhãn #qc, tránh từ bị cấm, dùng nhạc an toàn khi làm video tài trợ.",
    findingIds: VONG0_PREFLIGHT_FINDING_IDS,
  },
  {
    id: "v1",
    step: 1,
    title: "Vòng 1 — Hạt giống",
    subtitle: "Mức 100–500 lượt xem · đánh giá tài khoản",
    hint: "Nếu liên tục bị kẹt ở mức ~300 view, hãy mở TikTok → Cài đặt → Trạng thái tài khoản (Account Status) để kiểm tra. GetViews không tự quét được dữ liệu này.",
    findingIds: ACCOUNT_HEALTH_FINDING_IDS,
  },
  {
    id: "v2",
    step: 2,
    title: "Vòng 2 — Mở rộng",
    subtitle: "Định dạng video · phong cách · tần suất đăng · khung giờ",
    hint: "Giữ cố định 1–2 định dạng video chính; duy trì bối cảnh và câu nói thương hiệu ổn định trong 5 video tiếp theo.",
    findingIds: VONG2_FINDING_IDS,
  },
  {
    id: "v3",
    step: 3,
    title: "Vòng 3 — Xu hướng",
    subtitle: "Định dạng đối thủ · bão hòa nội dung",
    hint: "Tránh làm theo các định dạng đã quá quen thuộc của đối thủ trong ngách trong 7 ngày qua — hãy thử thay đổi tiêu đề (hook) hoặc chữ hiện trên màn hình.",
    findingIds: VONG3_VIRAL_FINDING_IDS,
  },
  {
    id: "v4",
    step: 4,
    title: "Vòng 4 — Ngách & khán giả",
    subtitle: "Hiệu suất gần đây · ngày siêu sale · từ khóa thịnh hành",
    hint: "So sánh view gần đây với thời kỳ đỉnh cao, cập nhật từ khóa Gen Z đang hot; chú ý lên lịch đăng tránh các đợt giảm tương tác ngày siêu sale.",
    findingIds: VONG4_AUDIENCE_FINDING_IDS,
  },
] as const;

const STRENGTH_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

export function policyRiskFindings(findings: ChannelDiagnosisFinding[]): ChannelDiagnosisFinding[] {
  return findings.filter((f) => POLICY_RISK_FINDING_IDS.has(f.finding_id));
}

export function accountHealthFindings(findings: ChannelDiagnosisFinding[]): ChannelDiagnosisFinding[] {
  return findings.filter((f) => ACCOUNT_HEALTH_FINDING_IDS.has(f.finding_id));
}

export function findingsForRing(
  ring: AuditRingDef,
  findings: ChannelDiagnosisFinding[],
): ChannelDiagnosisFinding[] {
  return findings
    .filter((f) => ring.findingIds.has(f.finding_id))
    .sort(
      (a, b) =>
        (STRENGTH_ORDER[a.strength] ?? 9) - (STRENGTH_ORDER[b.strength] ?? 9),
    );
}
