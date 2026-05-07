import { memo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, ChevronDown, Music2 } from "lucide-react";

import { VideoThumbnail } from "@/components/VideoThumbnail";
import { Btn } from "@/components/v2/Btn";
import { useDailyRitual, type RitualScript } from "@/hooks/useDailyRitual";
import { useRitualEvidenceVideos } from "@/hooks/useRitualEvidenceVideos";
import { analysisErrorCopy } from "@/lib/errorMessages";
import { formatRelativeSinceVi, formatViews } from "@/lib/formatters";
import { logUsage } from "@/lib/logUsage";
import { scriptPrefillFromRitual } from "@/lib/scriptPrefill";

/**
 * Studio Home — Tier 01 hero ("HÔM NAY QUAY NGAY") ranked list.
 *
 * Replaces the earlier HomeMorningRitual (3 cards) + NextVideosCard
 * (link to /app/answer) split — the design pack's
 * StudioHero (home.jsx:1154-1248) renders a single full-width ranked
 * list of idea rows, not a grid. Each row carries:
 *   • pad-zero rank ``01..NN``
 *   • mono uppercase HOOK badge
 *   • cyan ``● SCRIPT SẴN · X shot · Ys`` pill (every ritual script
 *     ships with a draft, so we always show the pill)
 *   • mono angle subtitle (hook_type_vi)
 *   • serif italicised quoted title (the actual hook text)
 *   • right column with ``▲ ~X%`` retention estimate + ``MỞ SCRIPT →``
 *
 * Click routes to ``/app/script`` with the idea preselected via
 * ``scriptPrefillFromRitual``.
 *
 * The BE stores one ritual row per (user, day, ``niche_id``) — up to three
 * per day for the three followed niches. Tier 01 loads the row for the
 * niche selected in the Home header.
 */

export const StudioHero = memo(function StudioHero({
  nicheId,
}: {
  nicheId: number | null;
}) {
  const { data: ritual, emptyReason, isPending, isError, error, refetch } = useDailyRitual(true, nicheId);
  const navigate = useNavigate();

  if (isPending) {
    return (
      <div className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-[18px]">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={
              "h-[100px] animate-pulse " +
              (i === 0 ? "" : "border-t border-[color:var(--gv-rule)]")
            }
          />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
        <p className="m-0 text-[14px] font-medium text-[color:var(--gv-danger)]">
          {analysisErrorCopy(error)}
        </p>
        <p className="mt-1.5">
          Gợi ý hôm nay tải từ máy chủ phân tích. Kiểm tra kết nối rồi thử lại — nếu vừa đổi ngách, có thể cần vài phút để job tạo kịch bản chạy.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Btn variant="ghost" size="sm" type="button" onClick={() => void refetch()}>
            Thử tải lại
          </Btn>
          <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/trends")}>
            Khám phá ngách
          </Btn>
        </div>
      </div>
    );
  }

  if (!ritual || ritual.scripts.length === 0) {
    const isNicheStale = emptyReason === "ritual_niche_stale";
    return (
      <div className="rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
        <p className="m-0 text-[14px] font-medium text-[color:var(--gv-ink)]">
          {isNicheStale ? "Kịch bản mới đang chuẩn bị cho ngách này" : "Đang tạo kịch bản cho ngày đầu"}
        </p>
        <p className="mt-1.5">
          {isNicheStale
            ? "Lần tạo kế tiếp sẽ có 3 kịch bản theo ngách bạn vừa chọn."
            : "Job hệ thống tạo kịch bản mỗi tối — sáng hôm sau sẽ thấy. Nếu lâu không có, bấm Thử tải lại."}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Btn variant="ghost" size="sm" type="button" onClick={() => void refetch()}>
            Thử tải lại
          </Btn>
          <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/trends")}>
            Khám phá ngách
          </Btn>
        </div>
      </div>
    );
  }

  const isThin = ritual.adequacy === "none" || ritual.adequacy === "reference_pool";
  const updatedRel = formatRelativeSinceVi(new Date(), new Date(ritual.generated_at));

  return (
    <div>
      <p className="gv-mono mb-3 text-[11px] text-[color:var(--gv-ink-4)]">
        Cập nhật · {updatedRel}
        {isThin ? (
          <span className="text-[color:var(--gv-ink-3)]">
            {" "}· Dữ liệu ngách đang thưa, các retention estimate là định hướng.
          </span>
        ) : null}
      </p>
      <div className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-[18px]">
        {ritual.scripts.map((s, i) => (
          <StudioHeroRow
            key={`${s.hook_type_en}-${i}`}
            script={s}
            rank={i + 1}
            isFirst={i === 0}
            onClick={() => {
              const nid = ritual?.niche_id ?? nicheId;
              if (nid == null) return;
              logUsage("daily_ritual_script_clicked", {
                niche_id: nid,
                rank: i + 1,
                hook_type_en: s.hook_type_en,
                shot_count: s.shot_count,
                length_sec: s.length_sec,
              });
              navigate(scriptPrefillFromRitual(s, nid));
            }}
          />
        ))}
      </div>
    </div>
  );
});

/**
 * L2.2 Sprint 3 — Sound Radar recommendation strip rendered inside each
 * StudioHero ritual row. Shows: 🔊 sound name · ↑+200% · 🔥 Đăng trong 48h
 * (or → · Tuần này for peaking). Renders nothing when ``sound_id`` is
 * absent — pre-Sprint-3 ritual rows look unchanged.
 */
const SoundRecommendationStrip = memo(function SoundRecommendationStrip({
  script,
}: {
  script: RitualScript;
}) {
  if (!script.sound_id || !script.sound_name) return null;

  const accelerating = script.sound_velocity === "accelerating";
  const trendArrow = accelerating ? "↑" : "→";
  const trendColor = accelerating
    ? "text-[color:var(--gv-pos-deep)]"
    : "text-[color:var(--gv-ink-3)]";

  // sound_delta_pct may be null (brand-new sound — no prev-week data),
  // so render the percentage only when we actually have a number.
  const deltaPct =
    typeof script.sound_delta_pct === "number" && Number.isFinite(script.sound_delta_pct)
      ? `${script.sound_delta_pct >= 0 ? "+" : ""}${Math.round(script.sound_delta_pct)}%`
      : null;

  const urgencyCopy =
    script.urgency_band === "post_within_48h"
      ? "🔥 Đăng trong 48h"
      : script.urgency_band === "this_week"
        ? "Tuần này"
        : null;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[color:var(--gv-ink-3)]">
      <span className="inline-flex items-center gap-1.5 max-w-full">
        <Music2 className="h-3 w-3 shrink-0 text-[color:var(--gv-ink-4)]" aria-hidden />
        <span className={`gv-mono ${trendColor}`} aria-hidden>
          {trendArrow}
        </span>
        <span className="truncate font-medium text-[color:var(--gv-ink-2)]">
          {script.sound_name}
        </span>
      </span>
      {deltaPct ? (
        <span className={`gv-mono text-[10px] ${trendColor}`}>{deltaPct}</span>
      ) : null}
      {urgencyCopy ? (
        <span
          className="gv-mono inline-flex items-center rounded-[2px] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em]"
          style={
            accelerating
              ? {
                  background: "color-mix(in srgb, var(--gv-accent) 14%, transparent)",
                  color: "var(--gv-accent-deep)",
                }
              : {
                  background: "var(--gv-canvas-2)",
                  color: "var(--gv-ink-3)",
                }
          }
        >
          {urgencyCopy}
        </span>
      ) : null}
    </div>
  );
});

/**
 * L2.2 Sprint 4 — Evidence strip per ritual row.
 *
 * Each ritual script ships up to 12 ``evidence_video_ids`` from the
 * grounding pool that match the script's ``hook_type_en``. This
 * component renders a collapsed "Xem N video tương tự ↓" trigger
 * inline; on expand, it hydrates the corpus rows via
 * ``useRitualEvidenceVideos`` and renders a horizontal-scroll thumbnail
 * strip. Clicking a thumbnail opens the original TikTok video in a new
 * tab — the goal here is *trust* (proof the hook is winning), not
 * triggering another diagnosis.
 *
 * Lives **outside** the row's primary ``<button>`` so the trigger
 * doesn't accidentally fire the "open script" navigation. Returns null
 * when ``evidence_video_ids`` is absent / empty (pre-Sprint-4 rows).
 */
const RitualEvidenceStrip = memo(function RitualEvidenceStrip({
  script,
  rank,
}: {
  script: RitualScript;
  rank: number;
}) {
  const ids = script.evidence_video_ids ?? [];
  const [expanded, setExpanded] = useState(false);
  const { data: videos, isPending, isError } = useRitualEvidenceVideos(ids, expanded);

  if (ids.length === 0) return null;

  const visibleCount = videos?.length ?? ids.length;

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => {
          if (!expanded) {
            logUsage("daily_ritual_evidence_expanded", {
              rank,
              hook_type_en: script.hook_type_en,
              evidence_count: ids.length,
            });
          }
          setExpanded((v) => !v);
        }}
        aria-expanded={expanded}
        aria-controls={`ritual-evidence-${rank}`}
        className="gv-mono inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)] hover:text-[color:var(--gv-ink-2)] transition-colors"
      >
        Xem {ids.length} video tương tự
        <ChevronDown
          className={"h-3 w-3 transition-transform " + (expanded ? "rotate-180" : "")}
          strokeWidth={2.2}
          aria-hidden
        />
      </button>
      {expanded ? (
        <div
          id={`ritual-evidence-${rank}`}
          className="mt-2 -mx-[18px] overflow-x-auto px-[18px]"
        >
          {isPending ? (
            <div className="flex gap-2">
              {Array.from({ length: Math.min(ids.length, 6) }).map((_, i) => (
                <div
                  key={i}
                  className="h-[120px] w-[68px] shrink-0 animate-pulse rounded-[3px] bg-[color:var(--gv-canvas-2)]"
                />
              ))}
            </div>
          ) : isError || !videos ? (
            <p className="text-[11px] text-[color:var(--gv-ink-4)]">
              Không tải được video tham chiếu — thử lại sau.
            </p>
          ) : visibleCount === 0 ? (
            <p className="text-[11px] text-[color:var(--gv-ink-4)]">
              Chưa có thumbnail cho hook này — kịch bản vẫn dùng được.
            </p>
          ) : (
            <ul className="flex gap-2" aria-label={`Video chứng minh hook #${rank}`}>
              {videos.map((v) => {
                const handle = (v.creator_handle ?? "").replace(/^@/, "");
                const href = handle
                  ? `https://www.tiktok.com/@${handle}/video/${v.video_id}`
                  : null;
                const Element = href ? "a" : "div";
                const interactiveProps = href
                  ? { href, target: "_blank" as const, rel: "noopener noreferrer" }
                  : {};
                return (
                  <li key={v.video_id} className="shrink-0">
                    <Element
                      {...interactiveProps}
                      className="block w-[68px]"
                      onClick={() =>
                        logUsage("daily_ritual_evidence_thumb_clicked", {
                          rank,
                          hook_type_en: script.hook_type_en,
                          video_id: v.video_id,
                        })
                      }
                    >
                      <VideoThumbnail
                        thumbnailUrl={v.thumbnail_url}
                        className="aspect-[9/12] w-full rounded-[3px] object-cover"
                      />
                      <span className="gv-mono mt-1 block truncate text-[9px] text-[color:var(--gv-ink-4)]">
                        {formatViews(v.views)}
                      </span>
                    </Element>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
});

const StudioHeroRow = memo(function StudioHeroRow({
  script,
  rank,
  isFirst,
  onClick,
}: {
  script: RitualScript;
  rank: number;
  isFirst: boolean;
  onClick: () => void;
}) {
  const rankLabel = String(rank).padStart(2, "0");
  return (
    <div
      className={
        "py-[18px] " +
        (isFirst ? "" : "border-t border-[color:var(--gv-rule)]")
      }
    >
      <button
        type="button"
        onClick={onClick}
        className="group grid w-full grid-cols-[40px_1fr_auto] items-center gap-x-4 gap-y-2 text-left transition-colors hover:bg-[color:var(--gv-canvas-2)]"
      >
        <span
          className="gv-mono self-start pt-1 text-[26px] font-semibold leading-none tracking-[-0.02em] text-[color:var(--gv-ink-4)]"
          aria-hidden
        >
          {rankLabel}
        </span>
        <div className="min-w-0">
          <div className="mb-1.5 flex flex-wrap items-center gap-2">
            <span className="gv-mono inline-flex items-center whitespace-nowrap rounded-[2px] bg-[color:var(--gv-ink)] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em] text-white">
              HOOK #{rank}
            </span>
            <span
              className="gv-mono inline-flex items-center gap-1 whitespace-nowrap rounded-[2px] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em]"
              style={{
                background: "color-mix(in srgb, var(--gv-pos) 12%, transparent)",
                color: "var(--gv-pos-deep)",
              }}
            >
              <span aria-hidden>●</span>
              SCRIPT SẴN · {script.shot_count} shot · {script.length_sec}s
            </span>
            {script.hook_type_vi ? (
              <span className="gv-mono text-[10px] font-medium text-[color:var(--gv-ink-4)]">
                {script.hook_type_vi}
              </span>
            ) : null}
          </div>
          <p
            className="gv-serif m-0 text-[19px] font-medium leading-[1.3] tracking-[-0.01em] text-[color:var(--gv-ink)]"
            style={{ textWrap: "pretty" }}
          >
            &ldquo;{script.title_vi}&rdquo;
          </p>
          {script.why_works ? (
            <p className="mt-1.5 text-[12.5px] leading-[1.5] text-[color:var(--gv-ink-3)]">
              {script.why_works}
            </p>
          ) : null}
          <SoundRecommendationStrip script={script} />
        </div>
        <div className="flex flex-col items-end gap-1 whitespace-nowrap">
          <span className="gv-mono text-[14px] font-bold" style={{ color: "var(--gv-pos)" }}>
            ▲ ~{script.retention_est_pct}%
          </span>
          <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">giữ chân</span>
          <span className="gv-mono mt-1 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[color:var(--gv-accent)] group-hover:translate-x-0.5 transition-transform">
            MỞ SCRIPT
            <ArrowRight className="h-3 w-3" strokeWidth={2.4} aria-hidden />
          </span>
        </div>
      </button>
      <RitualEvidenceStrip script={script} rank={rank} />
    </div>
  );
});
