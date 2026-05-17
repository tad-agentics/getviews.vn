/**
 * SectionRenderer — renders a single ChannelSection with its tiles.
 *
 * - verdict / what_worked / what_falling / video_vs_channel /
 *   competitive_landscape: h2 title + prose paragraphs + embedded tiles.
 * - recommendations: delegates to RecommendationList.
 * - fallback: renders raw text.
 */

import { SectionProseBlocks } from "@/components/SectionProseBlocks";
import type { ChannelSection, ChannelRecommendation } from "@/lib/api-types";
import { VideoTileRow } from "./VideoTileRow";
import { CreatorTileRow } from "./CreatorTileRow";
import { RecommendationList } from "./NumberedRecommendation";
import { HashtagInsightsBlock } from "./HashtagInsightsBlock";
import { NextVideoCard, NextVideoCardEmpty } from "./NextVideoCard";

interface SectionRendererProps {
  section: ChannelSection;
  recommendations?: ChannelRecommendation[];
  /** Whether text is still streaming in (shows trailing cursor on the
   * active section only — not every visible section). True iff the
   * stream is in flight AND this section is the currently-active one
   * (section_start fired, section_done has not). */
  streaming?: boolean;
}

export function SectionRenderer({
  section,
  recommendations = [],
  streaming = false,
}: SectionRendererProps) {
  const { section_id, title, text, embedded_tiles, embedded_creators, hashtag_insights, next_video } = section;

  if (section_id === "recommendations") {
    return (
      <div className="mb-6">
        <h2 className="text-base font-bold text-[color:var(--foreground)] leading-snug">
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
        <h2 className="text-base font-bold text-[color:var(--foreground)] leading-snug">{title}</h2>
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
        <h2 className="text-base font-bold text-[color:var(--foreground)] leading-snug">{title}</h2>
        {next_video ? (
          <NextVideoCard concept={next_video} streaming={streaming} />
        ) : (
          <NextVideoCardEmpty streaming={streaming} />
        )}
      </div>
    );
  }

  return (
    <div className="mb-6">
      {/* Section heading */}
      <h2 className="text-base font-bold text-[color:var(--foreground)] leading-snug">
        {title}
      </h2>

      {/* Prose body */}
      <div className="relative">
        <SectionProseBlocks text={text} />
        {streaming && !text && (
          // Active-section, no text_chunk yet — bridge the gap so the
          // section card isn't a bare heading for the second or two
          // between section_start and the first text_chunk landing.
          <p
            className="text-sm italic text-[color:var(--muted)] mt-2"
            aria-live="polite"
          >
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

      {/* Embedded video tiles */}
      {embedded_tiles && embedded_tiles.length > 0 && (
        <VideoTileRow tiles={embedded_tiles} />
      )}

      {/* Embedded creator tiles */}
      {embedded_creators && embedded_creators.length > 0 && (
        <CreatorTileRow creators={embedded_creators} />
      )}
    </div>
  );
}
