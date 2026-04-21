/**
 * Read-only legacy chat transcript (Phase C.7 — replaces interactive ChatScreen).
 */
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router";
import { ArrowLeft } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { useChatSession } from "@/hooks/useChatSession";
import { MarkdownRenderer } from "@/components/chat/MarkdownRenderer";
import { CreatorCard, type CreatorCardData } from "@/routes/_app/components/CreatorCard";
import {
  HookTimelineStrip,
  type HookTimelineEvent,
} from "@/routes/_app/components/HookTimelineStrip";
import {
  ThumbnailTile,
  type ThumbnailAnalysisData,
} from "@/routes/_app/components/ThumbnailTile";
import {
  CommentRadarTile,
  type CommentRadarData,
} from "@/routes/_app/components/CommentRadarTile";
import {
  PatternSpreadStrip,
  type TrendPattern,
} from "@/routes/_app/components/PatternSpreadStrip";
import {
  parseAssistantPayload,
  AssistantStructuredBlock,
} from "@/routes/_app/components/ChatTranscriptBlocks";

type ChatMsg = {
  id: string;
  role: string;
  content: string | null;
  intent_type?: string | null;
  is_free?: boolean | null;
  structured_output?: {
    follow_ups?: string[];
    coverage?: {
      niche_id?: number | null;
      niche_label?: string;
      corpus_count?: number;
      reference_count?: number;
      source?: string;
      freshness_days?: number;
    };
    creators?: CreatorCardData[];
    thumbnail_analysis?: ThumbnailAnalysisData;
    comment_radar?: CommentRadarData;
    patterns?: TrendPattern[];
    user_video?: {
      analysis?: {
        hook_analysis?: {
          hook_timeline?: HookTimelineEvent[];
        };
      };
      metadata?: { thumbnail_url?: string | null };
    };
  } | null;
};

export default function ChatSessionReadScreen() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { data: sessionRow, isLoading, isError } = useChatSession(sessionId ?? null);

  const messages = useMemo(
    () => (sessionRow?.chat_messages ?? []) as unknown as ChatMsg[],
    [sessionRow],
  );

  const title =
    sessionRow?.title?.trim() ||
    sessionRow?.first_message?.trim() ||
    "Phiên chat";

  return (
    <AppLayout active="answer" enableMobileSidebar>
      <div className="min-h-full bg-[var(--gv-canvas)] px-4 py-4 lg:px-10 lg:py-6">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/history")}>
            <ArrowLeft className="h-4 w-4" strokeWidth={1.8} />
            Lịch sử
          </Btn>
          <span className="font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">
            Phiên chat (chỉ đọc)
          </span>
        </div>

        <header className="mb-6 border-b border-[var(--gv-rule)] pb-4">
          <h1 className="gv-serif text-xl font-medium text-[var(--gv-ink)]">{title}</h1>
        </header>

        {isError ? (
          <p className="text-sm text-[var(--gv-danger)]">Không tải được phiên chat.</p>
        ) : isLoading ? (
          <p className="text-sm text-[var(--gv-ink-3)]">Đang tải…</p>
        ) : (
          <div className="space-y-4 overflow-x-hidden pb-24">
            {messages.map((m, idx) => {
              if (m.role === "user") {
                return (
                  <div key={m.id} className="flex justify-end overflow-hidden">
                    <div className="flex min-w-0 max-w-[85%] items-start gap-2 rounded-xl bg-[var(--gv-accent-soft)] px-4 py-3 lg:max-w-[75%]">
                      <p className="min-w-0 break-all text-sm text-[var(--ink)]">{m.content}</p>
                    </div>
                  </div>
                );
              }
              if (m.role === "assistant") {
                const parsed = parseAssistantPayload(m.content);
                const hasStructured =
                  parsed &&
                  ((parsed.diagnosis_rows && parsed.diagnosis_rows.length > 0) ||
                    (parsed.hook_ranking && parsed.hook_ranking.length > 0) ||
                    (parsed.brief_sections && parsed.brief_sections.length > 0) ||
                    (parsed.creators && parsed.creators.length > 0) ||
                    parsed.error_video);
                const hasPlain = parsed?.plain && parsed.plain.trim().length > 0;
                if (!hasStructured && !hasPlain) return null;
                const richCreators = m.structured_output?.creators ?? [];
                const hookTimeline =
                  m.structured_output?.user_video?.analysis?.hook_analysis?.hook_timeline ?? [];
                const thumbnailAnalysis = m.structured_output?.thumbnail_analysis ?? null;
                const thumbnailFrameUrl =
                  m.structured_output?.user_video?.metadata?.thumbnail_url ?? null;
                const commentRadar = m.structured_output?.comment_radar ?? null;
                const trendPatterns = m.structured_output?.patterns ?? [];
                return (
                  <div
                    key={m.id}
                    className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 lg:p-5"
                  >
                    {thumbnailAnalysis ? (
                      <ThumbnailTile data={thumbnailAnalysis} frameUrl={thumbnailFrameUrl} />
                    ) : null}
                    {commentRadar ? <CommentRadarTile data={commentRadar} /> : null}
                    {trendPatterns.length > 0 ? (
                      <PatternSpreadStrip patterns={trendPatterns} />
                    ) : null}
                    {hasStructured ? <AssistantStructuredBlock parsed={parsed} /> : null}
                    {hasPlain && !hasStructured ? (
                      <MarkdownRenderer text={parsed!.plain!} streaming={false} />
                    ) : null}
                    {hookTimeline.length > 0 ? (
                      <HookTimelineStrip events={hookTimeline} />
                    ) : null}
                    {richCreators.length > 0 ? (
                      <div className="mt-4 grid gap-3 border-t border-[var(--border)] pt-4">
                        {richCreators.map((c, i) => (
                          <CreatorCard
                            key={c.handle + i}
                            data={c}
                            index={i}
                            onAction={(_prompt: string) => {}}
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              }
              return null;
            })}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
