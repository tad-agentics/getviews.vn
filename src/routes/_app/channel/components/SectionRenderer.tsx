/**
 * SectionRenderer — renders a single ChannelSection with its tiles.
 *
 * - verdict / what_worked / what_falling / video_vs_channel /
 *   competitive_landscape: h2 title + prose paragraphs + embedded tiles.
 * - recommendations: delegates to RecommendationList.
 * - fallback: renders raw text.
 */

import { SectionProseBlocks } from "@/components/SectionProseBlocks";
import { splitVerdictProse } from "@/lib/humanizeStatsProse";
import type { ChannelSection, ChannelRecommendation, ChannelDiagnosisFinding } from "@/lib/api-types";
import { VideoTileRow } from "./VideoTileRow";
import { CreatorTileRow } from "./CreatorTileRow";
import { RecommendationList } from "./NumberedRecommendation";
import { HashtagInsightsBlock } from "./HashtagInsightsBlock";
import { NextVideoCard, NextVideoCardEmpty } from "./NextVideoCard";
import { PolicyRiskStrip } from "./PolicyRiskStrip";
import { AccountHealthStrip } from "./AccountHealthStrip";

interface SectionRendererProps {
  section: ChannelSection;
  recommendations?: ChannelRecommendation[];
  channelFindings?: ChannelDiagnosisFinding[];
  /** Whether text is still streaming in (shows trailing cursor on the
   * active section only — not every visible section). True iff the
   * stream is in flight AND this section is the currently-active one
   * (section_start fired, section_done has not). */
  streaming?: boolean;
}

export function SectionRenderer({
  section,
  recommendations = [],
  channelFindings = [],
  streaming = false,
}: SectionRendererProps) {
  const { section_id, title, text, embedded_tiles, embedded_creators, hashtag_insights, next_video } = section;

  if (section_id === "recommendations") {
    return (
      <div className="mb-6">
        <h2 className="gv-type-h3 text-[color:var(--foreground)] leading-snug">
          {title}
        </h2>
        {recommendations.length > 0 ? (
          <RecommendationList recommendations={recommendations} />
        ) : (
          <SectionProseBlocks text={text} />
        )}
      </div>
    );
  }

  if (section_id === "hashtag_insights") {
    return (
      <div className="mb-6">
        <h2 className="gv-type-h3 text-[color:var(--foreground)] leading-snug">{title}</h2>
        <HashtagInsightsBlock insights={hashtag_insights ?? []} />
        <div className="relative mt-2">
          <SectionProseBlocks text={text} />
          {streaming && text && (
            <span
              className="inline-block w-0.5 h-4 bg-[color:var(--primary)] animate-pulse ml-0.5 align-text-bottom"
              aria-hidden
            />
          )}
        </div>
      </div>
    );
  }

  if (section_id === "next_video") {
    return (
      <div className="mb-6">
        <h2 className="gv-type-h3 text-[color:var(--foreground)] leading-snug">{title}</h2>
        {next_video ? (
          <NextVideoCard concept={next_video} streaming={streaming} />
        ) : (
          <NextVideoCardEmpty streaming={streaming} />
        )}
      </div>
    );
  }

  if (section_id === "account_health") {
    return (
      <div className="mb-6">
        <h2 className="gv-type-h3 text-[color:var(--foreground)] leading-snug">{title}</h2>
        <AccountHealthStrip findings={channelFindings} />
        <div className="relative">
          <SectionProseBlocks text={text} />
          {streaming && !text && (
            <p className="text-sm italic text-[color:var(--muted)] mt-2" aria-live="polite">
              Đang viết phân tích…
            </p>
          )}
          {streaming && text && (
            <span
              className="inline-block w-0.5 h-4 bg-[color:var(--primary)] animate-pulse ml-0.5 align-text-bottom"
              aria-hidden
            />
          )}
        </div>
      </div>
    );
  }

  if (section_id === "policy_risk") {
    return (
      <div className="mb-6">
        <h2 className="gv-type-h3 text-[color:var(--foreground)] leading-snug">{title}</h2>
        <PolicyRiskStrip findings={channelFindings} />
        <div className="relative">
          <SectionProseBlocks text={text} />
          {streaming && !text && (
            <p className="text-sm italic text-[color:var(--muted)] mt-2" aria-live="polite">
              Đang viết phân tích…
            </p>
          )}
          {streaming && text && (
            <span
              className="inline-block w-0.5 h-4 bg-[color:var(--primary)] animate-pulse ml-0.5 align-text-bottom"
              aria-hidden
            />
          )}
        </div>
      </div>
    );
  }

  const { verdict, support } = splitVerdictProse(text);

  return (
    <div className="mb-6">
      <h2 className="gv-type-h3 text-[color:var(--foreground)] leading-snug">
        {title}
      </h2>

      {embedded_tiles && embedded_tiles.length > 0 ? (
        <VideoTileRow tiles={embedded_tiles} />
      ) : null}

      {embedded_creators && embedded_creators.length > 0 ? (
        <CreatorTileRow creators={embedded_creators} />
      ) : null}

      <div className="relative mt-3">
        {verdict ? (
          <p className="m-0 text-[17px] font-bold leading-snug text-[color:var(--foreground)]">
            {verdict}
          </p>
        ) : null}
        {support ? (
          <SectionProseBlocks
            text={support}
            paragraphClassName="text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]"
          />
        ) : !verdict && text.trim() ? (
          <SectionProseBlocks text={text} />
        ) : null}
        {streaming && !text && (
          <p
            className="mt-2 text-sm italic text-[color:var(--muted)]"
            aria-live="polite"
          >
            Đang viết phân tích…
          </p>
        )}
        {streaming && text ? (
          <span
            className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-[color:var(--primary)] align-text-bottom"
            aria-hidden
          />
        ) : null}
      </div>
    </div>
  );
}
