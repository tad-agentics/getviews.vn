import type { ChannelDiagnosisFinding } from "@/lib/api-types";

/** V5 audit rings — map finding_id → audit step footnote. */
export const ACCOUNT_HEALTH_FINDING_IDS = new Set([
  "channel_view_ceiling_300",
  "channel_boost_outlier_share",
]);

export const VONG2_FINDING_IDS = new Set([
  "channel_format_entropy_high",
  "channel_persona_drift",
  "channel_posting_cadence_vs_peer",
  "channel_best_hour_underused",
]);

export const VONG3_FINDING_IDS = new Set([
  "channel_compliance_aggregate",
  "channel_restricted_keyword_exposure",
  "channel_ad_law_disclosure_gap",
  "channel_copyright_mute_risk",
]);

export const VONG4_FINDING_IDS = new Set([
  "channel_recent_vs_peak_er_drop",
  "channel_peer_format_saturation",
  "channel_mega_sale_dip",
  "channel_slang_staleness",
]);

export const POLICY_RISK_FINDING_IDS = new Set([
  ...VONG3_FINDING_IDS,
]);

export const AUDIT_RING_HINTS: Array<{ ids: Set<string>; text: string }> = [
  {
    ids: ACCOUNT_HEALTH_FINDING_IDS,
    text: "Vòng 1 (sức khỏe tài khoản): nếu nhiều video kẹt ~300 view, mở TikTok → Cài đặt → Account Status. GetViews không đọc FYP %.",
  },
  {
    ids: VONG2_FINDING_IDS,
    text: "Vòng 2 (format & persona): thống nhất 1–2 format chủ đạo; giữ backdrop/catchphrase ổn định qua 5 video tiếp.",
  },
  {
    ids: VONG3_FINDING_IDS,
    text: "Vòng 3 (compliance): rà caption/VO — disclosure #qc, tránh cụm hạn chế, dùng sound CML-safe trước khi chạy brand.",
  },
  {
    ids: VONG4_FINDING_IDS,
    text: "Vòng 4 (audience & ngách): so recent vs peak, tránh copy format bão hòa peer; cập nhật slang theo Gen Z ngách.",
  },
];

export function policyRiskFindings(findings: ChannelDiagnosisFinding[]): ChannelDiagnosisFinding[] {
  return findings.filter((f) => POLICY_RISK_FINDING_IDS.has(f.finding_id));
}

export function accountHealthFindings(findings: ChannelDiagnosisFinding[]): ChannelDiagnosisFinding[] {
  return findings.filter((f) => ACCOUNT_HEALTH_FINDING_IDS.has(f.finding_id));
}

/** Top strip — exclude findings with dedicated memo section tiles (§5.5 Wave 2). */
export function summaryFindingsForStrip(findings: ChannelDiagnosisFinding[]): ChannelDiagnosisFinding[] {
  return findings.filter(
    (f) =>
      !POLICY_RISK_FINDING_IDS.has(f.finding_id) && !ACCOUNT_HEALTH_FINDING_IDS.has(f.finding_id),
  );
}

export function auditHintsForFindings(findings: ChannelDiagnosisFinding[]): string[] {
  const ids = new Set(findings.map((f) => f.finding_id));
  return AUDIT_RING_HINTS.filter(({ ids: ringIds }) => [...ringIds].some((id) => ids.has(id))).map(
    (ring) => ring.text,
  );
}
