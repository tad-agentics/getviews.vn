import { motion } from "motion/react";
import { CheckCircle2, AlertTriangle, Mail, Phone, ExternalLink } from "lucide-react";

export type CreatorTier = "nano" | "micro" | "macro" | "mega";

export type CreatorCardData = {
  handle: string;
  display_name: string | null;
  verified: boolean;
  avatar_url: string | null;
  bio_excerpt: string | null;

  followers: number;
  tier: CreatorTier;
  posting_frequency_per_week: number | null;
  days_since_last_post: number | null;

  niche_match: {
    primary_niche: string;
    confidence: number;
    secondary_niches: string[];
  };
  audience: {
    top_age_bucket: string | null;
    gender_skew: "female" | "male" | "balanced" | null;
    top_region: string | null;
  };

  engagement_rate_followers: number;
  comment_rate: number;
  median_views: number;
  engagement_trend: "rising" | "stable" | "declining" | null;

  best_video: {
    video_id: string;
    thumbnail_url: string | null;
    tiktok_url: string;
    views: number;
    why_it_worked: string;
  } | null;

  commerce: {
    shop_linked: boolean;
    recent_sponsored_count: number;
    competitor_conflicts: string[];
  };
  red_flags: string[];
  contact: {
    email: string | null;
    zalo: string | null;
    management: string | null;
  };

  reason: string;
  rate_ballpark: {
    currency: "VND";
    low: number;
    high: number;
    confidence: "observed" | "tier_estimate";
  } | null;

  actions: Array<{ type: string; prompt: string }>;
};

const TIER_LABEL: Record<CreatorTier, string> = {
  nano: "Nano",
  micro: "Micro",
  macro: "Macro",
  mega: "Mega",
};

function formatVN(n: number): string {
  return n.toLocaleString("vi-VN");
}

function formatVND(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)} triệu`;
  if (n >= 1_000) return `${formatVN(Math.round(n / 1_000))}K`;
  return formatVN(n);
}

function trendLabel(t: string | null): string | null {
  if (t === "rising") return "đang tăng ↑";
  if (t === "declining") return "đang giảm ↓";
  if (t === "stable") return "ổn định";
  return null;
}

function genderLabel(g: string | null): string | null {
  if (g === "female") return "nữ";
  if (g === "male") return "nam";
  if (g === "balanced") return "cân bằng";
  return null;
}

function redFlagLabel(f: string): string {
  switch (f) {
    case "engagement_anomaly":
      return "ER bất thường";
    case "post_gap":
      return "Ít đăng gần đây";
    case "declining_views":
      return "Views giảm";
    case "competitor_conflict":
      return "Đã quảng cáo đối thủ";
    default:
      return f;
  }
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  // Hide the row entirely if value is null/undefined/empty — per UX decision,
  // no empty placeholders.
  if (value == null || value === "" || value === false) return null;
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="flex-shrink-0 text-[var(--muted)]">{label}</span>
      <span className="text-[var(--ink)]">{value}</span>
    </div>
  );
}

export function CreatorCard({
  data,
  index,
  onAction,
}: {
  data: CreatorCardData;
  index: number;
  onAction: (prompt: string) => void;
}) {
  const trend = trendLabel(data.engagement_trend);
  const audienceBits = [
    data.audience.top_age_bucket,
    genderLabel(data.audience.gender_skew),
    data.audience.top_region,
  ].filter(Boolean);
  const audienceText = audienceBits.length ? audienceBits.join(" · ") : null;

  const postingText = (() => {
    const parts: string[] = [];
    if (typeof data.posting_frequency_per_week === "number" && data.posting_frequency_per_week > 0) {
      parts.push(`${data.posting_frequency_per_week.toFixed(1)} post/tuần`);
    }
    if (typeof data.days_since_last_post === "number") {
      parts.push(
        data.days_since_last_post === 0
          ? "đăng hôm nay"
          : `${data.days_since_last_post} ngày trước`,
      );
    }
    return parts.length ? parts.join(" · ") : null;
  })();

  const performanceText = (() => {
    const parts: string[] = [];
    if (data.engagement_rate_followers > 0)
      parts.push(`ER thật ${data.engagement_rate_followers.toFixed(1)}%`);
    if (data.median_views > 0) parts.push(`median ${formatVND(data.median_views)} views`);
    if (trend) parts.push(trend);
    return parts.length ? parts.join(" · ") : null;
  })();

  const commerceText = (() => {
    const parts: string[] = [];
    if (data.commerce.shop_linked) parts.push("TikTok Shop / Shopee");
    if (data.commerce.recent_sponsored_count > 0)
      parts.push(`${data.commerce.recent_sponsored_count} sponsored 90 ngày`);
    return parts.length ? parts.join(" · ") : null;
  })();

  const rate = data.rate_ballpark
    ? `${formatVND(data.rate_ballpark.low)}–${formatVND(data.rate_ballpark.high)} VND / post`
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.08, ease: "easeOut" }}
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
    >
      {/* Header: avatar + handle + tier */}
      <div className="flex items-start gap-3">
        {data.avatar_url ? (
          <img
            src={data.avatar_url}
            alt={data.handle}
            className="h-10 w-10 flex-shrink-0 rounded-full object-cover"
          />
        ) : (
          <div className="h-10 w-10 flex-shrink-0 rounded-full bg-[var(--surface-alt)]" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="truncate text-sm font-semibold text-[var(--ink)]">{data.handle}</p>
            {data.verified ? (
              <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-[var(--purple)]" strokeWidth={2.5} />
            ) : null}
            <span className="ml-auto flex-shrink-0 rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              {TIER_LABEL[data.tier]}
            </span>
          </div>
          <p className="truncate text-xs text-[var(--muted)]">
            {[data.display_name, data.followers > 0 ? `${formatVND(data.followers)} followers` : null]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
      </div>

      {/* Facts grid */}
      <div className="mt-3 flex flex-col gap-1.5">
        <Row
          label="Niche match"
          value={
            data.niche_match.confidence > 0
              ? `${Math.round(data.niche_match.confidence * 100)}% · ${data.niche_match.primary_niche}`
              : null
          }
        />
        <Row label="Audience" value={audienceText} />
        <Row label="Tần suất" value={postingText} />
        <Row label="Performance" value={performanceText} />
        <Row label="Commerce" value={commerceText} />
      </div>

      {/* Best video */}
      {data.best_video && data.best_video.video_id ? (
        <div className="mt-3 flex items-start gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-2.5">
          {data.best_video.thumbnail_url ? (
            <img
              src={data.best_video.thumbnail_url}
              alt="best video"
              className="h-16 w-12 flex-shrink-0 rounded object-cover"
            />
          ) : (
            <div className="h-16 w-12 flex-shrink-0 rounded bg-[var(--border)]" />
          )}
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-[var(--ink)]">
              Video hay nhất · {formatVND(data.best_video.views)} views
            </p>
            <p className="mt-0.5 text-xs text-[var(--muted)]">
              {data.best_video.why_it_worked}
            </p>
            {data.best_video.tiktok_url ? (
              <a
                href={data.best_video.tiktok_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex items-center gap-1 text-[10px] font-semibold text-[var(--purple)] hover:underline"
              >
                Mở trên TikTok <ExternalLink className="h-2.5 w-2.5" strokeWidth={2.5} />
              </a>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Red flags */}
      {data.red_flags.length > 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-500" strokeWidth={2.5} />
          {data.red_flags.map((f) => (
            <span
              key={f}
              className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-300"
            >
              {redFlagLabel(f)}
            </span>
          ))}
        </div>
      ) : null}

      {/* Contact */}
      {(data.contact.email || data.contact.zalo || data.contact.management) ? (
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-[var(--muted)]">
          {data.contact.email ? (
            <span className="inline-flex items-center gap-1">
              <Mail className="h-3 w-3" strokeWidth={2} />
              <span className="break-all text-[var(--ink)]">{data.contact.email}</span>
            </span>
          ) : null}
          {data.contact.zalo ? (
            <span className="inline-flex items-center gap-1">
              <Phone className="h-3 w-3" strokeWidth={2} />
              <span className="text-[var(--ink)]">Zalo {data.contact.zalo}</span>
            </span>
          ) : null}
          {data.contact.management ? (
            <span className="inline-flex items-center gap-1">
              <span className="text-[var(--muted)]">MCN:</span>
              <span className="text-[var(--ink)]">{data.contact.management}</span>
            </span>
          ) : null}
        </div>
      ) : null}

      {/* Reason + rate */}
      <div className="mt-3 border-t border-[var(--border)] pt-3">
        <p className="text-xs font-semibold text-[var(--ink)]">Vì sao hợp với bạn</p>
        <p className="mt-1 whitespace-pre-line text-xs leading-relaxed text-[var(--muted)]">
          {data.reason}
        </p>
        {rate ? (
          <p className="mt-2 text-xs text-[var(--faint)]">
            Giá ước ({TIER_LABEL[data.tier]} tier): <span className="text-[var(--ink)]">{rate}</span>
          </p>
        ) : null}
      </div>

      {/* Action chips */}
      {data.actions.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {data.actions.map((a, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onAction(a.prompt)}
              className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-[11px] font-medium text-[var(--ink)] transition-all duration-[120ms] hover:border-[var(--border-active)] hover:shadow-sm active:scale-[0.98]"
            >
              {a.prompt}
            </button>
          ))}
        </div>
      ) : null}
    </motion.div>
  );
}
