import { useState, useRef, useEffect, useMemo, useCallback, memo } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import {
  Plus,
  Image as ImageIcon,
  TrendingUp,
  Video,
  Search,
  BarChart2,
  ArrowUp,
  Database,
  X,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import {
  useChatSession,
  useCreateSession,
  useInsertUserMessage,
} from "@/hooks/useChatSession";
import { useChatStream } from "@/hooks/useChatStream";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { DiagnosisRow, type DiagnosisRowData } from "@/routes/_app/components/DiagnosisRow";
import { ThumbnailStrip, type ThumbnailItem } from "@/routes/_app/components/ThumbnailStrip";
import { CopyButton } from "@/routes/_app/components/CopyButton";
import { URLChip } from "@/routes/_app/components/URLChip";
import { PromptCards } from "@/routes/_app/components/PromptCards";
import { MobileEmptyState, DesktopCenteredEmpty } from "@/routes/_app/components/EmptyStates";
import { QuickActionModal } from "@/routes/_app/components/QuickActionModal";
import { StreamingStatusText } from "@/routes/_app/components/StreamingStatusText";
import { FreeQueryPill } from "@/routes/_app/components/FreeQueryPill";
import { NicheSelector } from "@/routes/_app/components/NicheSelector";
import { HookRankingBar } from "@/routes/_app/components/HookRankingBar";
import { BriefBlock } from "@/routes/_app/components/BriefBlock";
import { CreatorCard } from "@/routes/_app/components/CreatorCard";
import { MarkdownRenderer } from "@/components/chat/MarkdownRenderer";
import { AgentStepLogger } from "@/components/chat/AgentStepLogger";

type ChatMsg = {
  id: string;
  role: string;
  content: string | null;
  intent_type?: string | null;
  is_free?: boolean | null;
};

const FREE_INTENT_SET = new Set(["find_creators", "trend_spike", "follow_up"]);

/** Tier-3: ask the backend to classify intent using Gemini when tiers 1+2 are low-confidence. */
async function classifyIntentT3(
  query: string,
  accessToken: string,
): Promise<{ intentType: string; isFree: boolean }> {
  const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
  if (!cloudRunUrl) return { intentType: "follow_up", isFree: true };
  try {
    const res = await fetch(`${cloudRunUrl}/classify-intent`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error(`classify-intent HTTP ${res.status}`);
    const data = (await res.json()) as { primary?: string; secondary?: string | null };
    const intentType = data.primary ?? "follow_up";
    return { intentType, isFree: FREE_INTENT_SET.has(intentType) };
  } catch {
    return { intentType: "follow_up", isFree: true };
  }
}

function isResumeQuery(q: string): boolean {
  const s = q.trim().toLowerCase();
  return ["tiếp", "tiếp tục", "continue", "resume", "/tiếp"].includes(s);
}

/**
 * detectIntent — maps a raw user message to a pipeline intent.
 *
 * Intent catalogue:
 *   video_diagnosis    — analyse a specific video URL (why it flopped / how to improve)
 *   competitor_profile — analyse another creator's channel via @handle or profile URL
 *   own_channel        — analyse the user's own channel
 *   series_audit       — let backend handle; we route all multi-URL to video_diagnosis here
 *   trend_spike        — what's trending / viral right now in a niche
 *   content_directions — what video types / formats / hooks to make next
 *   brief_generation   — produce a full content brief (default fallback)
 *   shot_list          — production shot list / filming plan for a video
 *   find_creators      — discover KOLs / creators in a niche
 *   follow_up          — continue the current conversation thread
 *
 * Priority order: URL → handle → shot_list → find_creators → own_channel
 *                 → content_directions + trend (with disambiguation)
 *                 → trend_spike alone → default (low confidence → tier 3)
 *
 * Returns a `confidence` flag:
 *   "high"   — structural signal (URL, handle) — always correct, no tier-3 needed
 *   "medium" — keyword matched — usually correct
 *   "low"    — fell through to follow_up with no prior context — tier-3 needed
 */
function detectIntent(
  query: string,
  priorAssistant: boolean,
): { intentType: string; isFree: boolean; confidence: "high" | "medium" | "low" } {
  const q = query.trim();
  const ql = q.toLowerCase();

  // ── 1. URL DETECTION (highest confidence — structural) ────────────────────
  if (/https?:\/\/[^\s]*tiktok\.com/i.test(q)) {
    const hasTiktokProfileUrl = /tiktok\.com\/@[^\s/]+(?:\/(?!video|photo)[^\s]*)?(?:\s|$)/i.test(q)
      && !/\/video\//i.test(q)
      && !/\/photo\//i.test(q);
    return hasTiktokProfileUrl
      ? { intentType: "competitor_profile", isFree: false, confidence: "high" }
      : { intentType: "video_diagnosis", isFree: false, confidence: "high" };
  }

  // ── 2. HANDLE DETECTION (structural) ─────────────────────────────────────
  if (/@\w/.test(q)) {
    const ownChannelHandle = /soi kênh|kênh (của )?(mình|tôi|tao|tui)|review kênh|phân tích kênh|đánh giá kênh|channel (của )?(mình|tôi|tao|tui)/i.test(ql);
    return ownChannelHandle
      ? { intentType: "own_channel", isFree: false, confidence: "high" }
      : { intentType: "competitor_profile", isFree: false, confidence: "high" };
  }

  // ── 3. SHOT LIST ──────────────────────────────────────────────────────────
  if (/shot list|kịch bản|cách quay|hướng dẫn quay|quay như nào|quay thế nào|quay video|lên ý tưởng quay|plan quay|danh sách cảnh|cảnh quay/i.test(ql)) {
    return { intentType: "shot_list", isFree: false, confidence: "medium" };
  }

  // ── 4. FIND CREATORS ──────────────────────────────────────────────────────
  if (/tìm creator|tìm kol|tìm koc|ai đang làm tốt|creator nào|kol nào|koc nào|giới thiệu creator|gợi ý kol|gợi ý creator/i.test(ql)) {
    return { intentType: "find_creators", isFree: true, confidence: "medium" };
  }

  // ── 5. OWN CHANNEL ────────────────────────────────────────────────────────
  if (/soi kênh|kênh (của )?(mình|tôi|tao|tui)|review kênh|phân tích kênh|đánh giá kênh|channel (của )?(mình|tôi|tao)/i.test(ql)) {
    return { intentType: "own_channel", isFree: false, confidence: "medium" };
  }

  // ── 6. CONTENT_DIRECTIONS + TREND disambiguation ──────────────────────────
  const isTrend = /đang viral|video viral|viral rồi|xu hướng|đang lên|bùng nổ|đang nổ|gì đang chạy|trend|tuần này|7 ngày|gần đây|đang trending|mới nổi/i.test(ql)
    || /\b(trending|viral)\b/i.test(ql);

  const isContent = /nên quay gì|quay gì|làm gì|video gì|format nào|hook nào|kiểu video|đang chạy tốt|đang work|đang hiệu quả|hướng content|content direction|hướng nội dung|nên làm gì|nên làm video|ý tưởng video|gì đang hot|gợi ý nội dung|loại video/i.test(ql);

  if (isContent) return { intentType: "content_directions", isFree: false, confidence: "medium" };
  if (isTrend) return { intentType: "trend_spike", isFree: true, confidence: "medium" };

  // ── 7. DEFAULT ────────────────────────────────────────────────────────────
  // follow_up with prior context = medium confidence (conversation continuation).
  // follow_up with NO prior context = low confidence → tier-3 Gemini classification.
  return {
    intentType: "follow_up",
    isFree: true,
    confidence: priorAssistant ? "medium" : "low",
  };
}

type ParsedAssistant = {
  diagnosis_rows?: DiagnosisRowData[];
  corpus_cite?: { count: number; niche: string; timeframe: string; updated_hours_ago?: number };
  thumbnails?: ThumbnailItem[];
  hook_ranking?: { label: string; percent: number }[];
  brief_sections?: string[];
  creators?: { handle: string; meta: string }[];
  error_video?: boolean;
  plain?: string;
};

function parseAssistantPayload(content: string | null): ParsedAssistant | null {
  if (!content || !content.trim()) return null;
  const t = content.trim();
  if (t.startsWith("{")) {
    try {
      return JSON.parse(t) as ParsedAssistant;
    } catch {
      return { plain: content };
    }
  }
  return { plain: content };
}

const VIDEO_INTENTS = new Set(["video_diagnosis", "competitor_profile", "own_channel"]);

function buildCopyPlain(parsed: ParsedAssistant | null): string {
  if (parsed?.plain) return parsed.plain;
  const rows = parsed?.diagnosis_rows ?? [];
  if (rows.length) return rows.map((d) => `${d.type === "fail" ? "✕" : "✓"} ${d.finding}`).join("\n");
  return "";
}

function AssistantStructuredBlock({ parsed }: { parsed: ParsedAssistant | null }) {
  if (!parsed) return null;
  const diagnosis = parsed.diagnosis_rows ?? [];
  const cite = parsed.corpus_cite;
  const thumbs = parsed.thumbnails ?? [];
  const copyPlain = buildCopyPlain(parsed);

  return (
    <>
      {parsed.error_video ? (
        <p className="mb-3 text-sm text-[var(--danger)]">
          Video không tải được — thử dán lại hoặc dùng video khác.
        </p>
      ) : null}
      {diagnosis.length > 0 ? (
        <>
          <p className="mb-4 text-sm text-[var(--muted)]">
            Đã so sánh với {cite?.count ?? "—"} video trong niche —
          </p>
          <div className="mb-4 space-y-1 divide-y divide-[var(--border)]">
            {diagnosis.map((row, idx) => (
              <DiagnosisRow key={`${row.finding}-${idx}`} row={row} index={idx} />
            ))}
          </div>
          {cite ? (
            <p className="mb-4 font-mono text-xs text-[var(--faint)]">
              {cite.count} video {cite.niche} · {cite.timeframe}
              {cite.updated_hours_ago != null ? ` · Cập nhật ${cite.updated_hours_ago}h trước` : ""}
            </p>
          ) : null}
          {thumbs.length > 0 ? (
            <div className="mb-4">
              <ThumbnailStrip thumbnails={thumbs} />
            </div>
          ) : null}
          <CopyButton textToCopy={copyPlain} />
        </>
      ) : null}
      {parsed.hook_ranking?.length ? (
        <div className="mt-4 border-t border-[var(--border)] pt-4">
          {parsed.hook_ranking.map((h, i) => (
            <HookRankingBar key={i} label={h.label} percent={h.percent} />
          ))}
        </div>
      ) : null}
      {parsed.brief_sections?.length ? (
        <div className="mt-4 border-t border-[var(--border)] pt-4">
          <BriefBlock sections={parsed.brief_sections} />
        </div>
      ) : null}
      {parsed.creators?.length ? (
        <div className="mt-4 grid gap-2 border-t border-[var(--border)] pt-4">
          {parsed.creators.map((c, i) => (
            <CreatorCard key={i} handle={c.handle} meta={c.meta} index={i} />
          ))}
        </div>
      ) : null}
      {parsed.plain && !diagnosis.length ? (
        <MarkdownRenderer text={parsed.plain} />
      ) : null}
    </>
  );
}

const DesktopInput = memo(function DesktopInput({
  message,
  setMessage,
  onSend,
  inputDisabled,
  needsNiche,
  userId,
  credits,
  onNavigatePricing,
}: {
  message: string;
  setMessage: (v: string) => void;
  onSend: () => void;
  inputDisabled: boolean;
  needsNiche: boolean;
  userId: string | undefined;
  credits: number;
  onNavigatePricing: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const charCount = message.length;
  const charLimit = 1000;
  const charOverLimit = charCount > charLimit;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [message]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="flex-shrink-0 px-10 pb-7">
      {needsNiche && userId ? (
        <div className="mb-4">
          <NicheSelector userId={userId} />
        </div>
      ) : null}
      {credits > 0 && credits <= 5 ? (
        <div className="mb-3 flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 dark:border-amber-900/40 dark:bg-amber-950/30">
          <p className="text-xs text-amber-800 dark:text-amber-300">
            Còn <span className="font-semibold">{credits}</span> deep credit — mỗi phân tích sâu dùng 1 credit.
          </p>
          <button
            type="button"
            onClick={onNavigatePricing}
            className="ml-3 shrink-0 text-xs font-semibold text-amber-700 hover:underline dark:text-amber-400"
          >
            Nạp thêm →
          </button>
        </div>
      ) : null}
      <div
        className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]"
        style={{ boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)" }}
      >
        <div className="px-4 pb-2 pt-4">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Dán link TikTok hoặc hỏi bất cứ thứ gì..."
            rows={1}
            maxLength={charLimit + 50}
            disabled={inputDisabled}
            className="w-full resize-none overflow-hidden border-none bg-transparent text-sm leading-relaxed text-[var(--ink)] outline-none placeholder:text-[var(--faint)] disabled:opacity-50"
            style={{ minHeight: 28, fontSize: 14 }}
          />
        </div>
        <div className="flex items-center justify-between px-3 pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-[var(--muted)] transition-colors duration-[120ms] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)]"
            >
              <Plus className="h-3.5 w-3.5" strokeWidth={1.8} />
              <span>Đính kèm</span>
            </button>
            <button
              type="button"
              className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-[var(--muted)] transition-colors duration-[120ms] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)]"
            >
              <ImageIcon className="h-3.5 w-3.5" strokeWidth={1.8} />
              <span>Dùng ảnh</span>
            </button>
          </div>
          <div className="flex items-center gap-2">
            {charCount > 0 ? (
              <span
                className={`font-mono text-xs tabular-nums ${
                  charOverLimit ? "text-[var(--danger)]" : "text-[var(--faint)]"
                }`}
              >
                {charCount}/{charLimit}
              </span>
            ) : null}
            <button
              type="button"
              disabled={!message.trim() || charOverLimit || inputDisabled}
              onClick={onSend}
              className="flex h-8 w-8 items-center justify-center rounded-full transition-all duration-[120ms] active:scale-95"
              style={{
                background: message.trim() && !charOverLimit && !inputDisabled ? "var(--gradient-primary)" : "var(--faint)",
                cursor: !message.trim() || charOverLimit || inputDisabled ? "not-allowed" : "pointer",
              }}
            >
              <ArrowUp className="h-4 w-4 text-white" strokeWidth={2.5} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

export default function ChatScreen() {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlSessionId = searchParams.get("session");
  const [sessionId, setSessionId] = useState<string | null>(urlSessionId);

  const { data: profile } = useProfile();
  const { data: sessionRow, refetch: refetchSession, status: sessionStatus } = useChatSession(sessionId);
  const createSession = useCreateSession();
  const insertUser = useInsertUserMessage();
  const { status, text, streamId, lastSeq, error, stepEvents, stream, reset } = useChatStream();
  const { data: nicheRows } = useNicheTaxonomy();

  const messages = useMemo(
    () => (sessionRow?.chat_messages ?? []) as unknown as ChatMsg[],
    [sessionRow],
  );

  const nicheLabel = useMemo(() => {
    const pn = profile?.primary_niche;
    if (pn == null) return "";
    return nicheRows?.find((n) => n.id === pn)?.name ?? "";
  }, [profile?.primary_niche, nicheRows]);

  const [message, setMessage] = useState("");
  const [showMessages, setShowMessages] = useState(false);

  useEffect(() => {
    const prefillUrl = (location.state as { prefillUrl?: string } | null | undefined)?.prefillUrl;
    if (!prefillUrl || typeof prefillUrl !== "string") return;
    setMessage(prefillUrl);
    navigate(`${location.pathname}${location.search}`, { replace: true, state: {} });
  }, [location.state, location.pathname, location.search, navigate]);
  const [freePillKey, setFreePillKey] = useState(0);
  const [clientPaywall, setClientPaywall] = useState(false);
  const [lastStreamIntent, setLastStreamIntent] = useState<string | null>(null);
  const lastIntentRef = useRef<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync session state with URL ?session= param on every navigation
  useEffect(() => {
    const s = searchParams.get("session");
    if (s) {
      // Navigated to a specific session (e.g. from history sidebar)
      setSessionId(s);
      setShowMessages(true);
    } else {
      // No ?session= — new chat button or bare /app navigation
      setSessionId(null);
      setShowMessages(false);
      setClientPaywall(false);
      setLastStreamIntent(null);
      lastIntentRef.current = null;
      reset();
      // Only clear the message box if there's no incoming prefillUrl from location state
      // (e.g. "Phân tích video này" button in ExploreScreen passes tiktok_url via state)
      const hasPrefill = !!(location.state as { prefillUrl?: string } | null)?.prefillUrl;
      if (!hasPrefill) setMessage("");
    }
  // reset is stable (useCallback), searchParams identity changes on navigation
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Guard: session was deleted externally or URL is stale — reset to new chat
  useEffect(() => {
    if (sessionId && sessionStatus === "error") {
      navigate("/app");
    }
  }, [sessionId, sessionStatus, navigate]);

  useEffect(() => {
    if (messages.length > 0) setShowMessages(true);
  }, [messages.length]);

  const credits = profile?.deep_credits_remaining ?? 0;
  const processing = Boolean(profile?.is_processing);
  const needsNiche = profile?.primary_niche == null;

  const priorAssistant = useMemo(() => messages.some((m) => m.role === "assistant"), [messages]);

  const lastUser = useMemo(() => [...messages].reverse().find((m) => m.role === "user"), [messages]);

  const hasTikTokUrl = message.includes("tiktok.com");
  const charCount = message.length;
  const charLimit = 1000;
  const charOverLimit = charCount > charLimit;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 96)}px`;
  }, [message]);

  const runSend = useCallback(
    async (raw: string, resume?: { stream_id: string; last_seq: number }) => {
      const trimmed = raw.trim();
      if (!trimmed || trimmed.length > charLimit || !user?.id) return;
      if (processing) return;

      setClientPaywall(false);

      const isResume = Boolean(resume && lastIntentRef.current);
      let intentType: string;
      let isFree: boolean;

      if (isResume) {
        intentType = lastIntentRef.current!;
        isFree = true;
      } else {
        const detected = detectIntent(trimmed, priorAssistant);
        if (detected.confidence === "low") {
          // Tier-3: Gemini semantic classification — fires only when tiers 1+2 are ambiguous
          const { data: { session: authSession } } = await supabase.auth.getSession();
          const classified = authSession
            ? await classifyIntentT3(trimmed, authSession.access_token)
            : { intentType: "follow_up", isFree: true };
          intentType = classified.intentType;
          isFree = classified.isFree;
        } else {
          intentType = detected.intentType;
          isFree = detected.isFree;
        }
      }

      if (!isFree && credits <= 0) {
        setClientPaywall(true);
        return;
      }

      setShowMessages(true);

      let sid = sessionId;
      if (!sid) {
        const row = await createSession.mutateAsync({
          userId: user.id,
          nicheId: profile?.primary_niche ?? null,
        });
        sid = row.id;
        setSessionId(sid);
        setSearchParams({ session: sid }, { replace: true });
      }

      await insertUser.mutateAsync({
        sessionId: sid!,
        userId: user.id,
        content: trimmed,
        intentType,
        isFree,
      });

      setLastStreamIntent(intentType);
      lastIntentRef.current = intentType;

      await stream({
        sessionId: sid!,
        query: trimmed,
        intentType,
        resumeStreamId: resume?.stream_id,
        lastSeq: resume?.last_seq,
      });

      await refetchSession();
      if (isFree) setFreePillKey((k) => k + 1);
      reset();
    },
    [
      charLimit,
      user?.id,
      processing,
      priorAssistant,
      credits,
      sessionId,
      profile?.primary_niche,
      createSession,
      setSearchParams,
      insertUser,
      stream,
      refetchSession,
      reset,
    ],
  );

  const handleSend = async (overrideText?: string) => {
    const q = overrideText ?? message;
    if (!q.trim() || q.length > charLimit) return;
    const trimmed = q.trim();
    const resumePayload =
      isResumeQuery(trimmed) &&
      status === "error" &&
      streamId !== null &&
      error !== "insufficient_credits" &&
      error !== "daily_free_limit" &&
      lastIntentRef.current !== null
        ? { stream_id: streamId, last_seq: lastSeq }
        : undefined;
    setMessage("");
    if (!resumePayload) reset();
    await runSend(q, resumePayload);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const inputDisabled = authLoading || processing || insertUser.isPending || status === "streaming";

  const paywallVisible = clientPaywall || error === "insufficient_credits";
  const dailyLimitVisible = error === "daily_free_limit";

  // Keep the in-flight block visible during streaming AND while the stream is
  // "done" but the TanStack Query refetch hasn't landed yet (the gap between
  // invalidateQueries() and the new assistant row appearing in `messages`).
  // Without this, the streamed text disappears for ~200–500ms after completion.
  const lastMessageIsAssistant = messages.at(-1)?.role === "assistant";
  const inFlightVisible =
    status === "streaming" ||
    (status === "done" && Boolean(text) && !lastMessageIsAssistant);

  // Error block is rendered independently — never hidden by DB refetch landing.
  const streamErrorVisible =
    status === "error" && error !== "insufficient_credits" && error !== "daily_free_limit";

  const messageThread = (
    <div className="space-y-4 overflow-x-hidden">
      {dailyLimitVisible ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/40 dark:bg-amber-950/30">
          <p className="text-sm text-amber-800 dark:text-amber-300">
            Bạn đã dùng quá 100 lượt tìm kiếm hôm nay. Hạn mức sẽ reset lúc 00:00 ngày mai.
          </p>
        </div>
      ) : null}
      {paywallVisible ? (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="mb-3 text-sm text-[var(--ink)]">
            Hết deep credit tháng này. Mua thêm 10 credit = 130.000 VND.
          </p>
          <button
            type="button"
            onClick={() => navigate("/app/pricing")}
            className="inline-flex text-sm font-semibold text-[var(--purple)] hover:underline"
          >
            Mua thêm →
          </button>
        </div>
      ) : null}

      {messages.map((m) => {
        if (m.role === "user") {
          return (
            <div key={m.id} className="flex justify-end overflow-hidden">
              <div className="flex min-w-0 max-w-[85%] items-start gap-2 rounded-xl bg-[var(--purple-light)] px-4 py-3 lg:max-w-[75%]">
                <p className="min-w-0 break-all text-sm text-[var(--ink)]">{m.content}</p>
                {m.is_free && m.id === lastUser?.id ? <FreeQueryPill pulseKey={freePillKey} /> : null}
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
          return (
            <div key={m.id} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 lg:p-5">
              {hasStructured ? <AssistantStructuredBlock parsed={parsed} /> : null}
              {hasPlain && !hasStructured ? (
                <MarkdownRenderer text={parsed!.plain!} streaming={false} />
              ) : null}
            </div>
          );
        }
        return null;
      })}

      {inFlightVisible ? (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 lg:p-5">
          {/* Step logger — shown before synthesis text arrives */}
          {stepEvents.length > 0 ? (
            <AgentStepLogger events={stepEvents} collapsed={Boolean(text)} />
          ) : (
            <StreamingStatusText
              phase={status === "streaming" ? "streaming" : "idle"}
              isVideoIntent={VIDEO_INTENTS.has(lastStreamIntent ?? "")}
            />
          )}
          {status === "streaming" && !text && stepEvents.length === 0 ? (
            <div className="mt-3">
              <div className="space-y-2 animate-pulse">
                <div className="h-3 w-[75%] rounded bg-[var(--border)]" />
                <div className="h-3 w-[50%] rounded bg-[var(--border)]" />
                <div className="h-3 w-[66%] rounded bg-[var(--border)]" />
              </div>
              <p className="mt-2 text-xs text-[var(--faint)]">Đang kết nối và phân tích...</p>
            </div>
          ) : null}
          {text ? (
            <div className="mt-2">
              <MarkdownRenderer text={text} streaming={status === "streaming"} />
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Error block — rendered independently so a DB refetch can never hide it */}
      {streamErrorVisible ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-900/40 dark:bg-red-950/30">
          <p className="text-sm text-red-700 dark:text-red-300">
            {error === "analysis_timeout"
              ? "Phân tích quá lâu — thử lại với video ngắn hơn hoặc gõ 'tiếp'."
              : error === "video_download_failed"
                ? "Không tải được video — link có thể đã hết hạn. Thử dán lại link mới."
                : error === "ensembledata_quota"
                  ? "Hệ thống đang quá tải — thử lại sau vài phút."
                  : error === "gemini_error"
                    ? "AI tạm lỗi — thử lại sau ít phút."
                    : error === "missing_video_url"
                      ? "Cần link TikTok video hợp lệ (dán link vào tin nhắn)."
                      : "Có lỗi xảy ra — gõ 'tiếp' để thử lại hoặc gửi câu hỏi mới."}
          </p>
        </div>
      ) : null}

      <div ref={messagesEndRef} />
    </div>
  );

  return (
    <AppLayout active="chat" enableMobileSidebar>
      <div className="hidden h-full flex-col lg:flex">
        {!showMessages ? (
          <DesktopCenteredEmpty
            nicheLabel={nicheLabel}
            initialValue={message}
            inputDisabled={inputDisabled}
            needsNiche={needsNiche}
            userId={user?.id}
            onSend={(text) => void handleSend(text)}
          />
        ) : (
          <>
            <div className="flex-1 space-y-4 overflow-y-auto px-10 py-6">{messageThread}</div>
            <DesktopInput
              message={message}
              setMessage={setMessage}
              onSend={() => void handleSend()}
              inputDisabled={inputDisabled}
              needsNiche={needsNiche}
              userId={user?.id}
              credits={credits}
              onNavigatePricing={() => navigate("/app/pricing")}
            />
          </>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:hidden">
        <div className="flex-1 overflow-y-auto bg-[var(--surface-alt)]">
          {!showMessages ? (
            <MobileEmptyState
              nicheLabel={nicheLabel}
              onSelectPrompt={(p) => {
                setMessage(p);
                setShowMessages(true);
              }}
            />
          ) : (
            <div className="mx-auto max-w-2xl px-4 py-4">{messageThread}</div>
          )}
        </div>

        <div className="flex-shrink-0 border-t border-[var(--border)] bg-[var(--surface)] px-3 py-3">
          <div className="mx-auto max-w-2xl">
            {needsNiche && user?.id ? (
              <div className="mb-3">
                <NicheSelector userId={user.id} />
              </div>
            ) : null}
            {credits > 0 && credits <= 5 ? (
              <div className="mb-2 flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-900/40 dark:bg-amber-950/30">
                <p className="text-[11px] text-amber-800 dark:text-amber-300">
                  Còn <span className="font-semibold">{credits}</span> deep credit
                </p>
                <button
                  type="button"
                  onClick={() => navigate("/app/pricing")}
                  className="ml-2 shrink-0 text-[11px] font-semibold text-amber-700 hover:underline dark:text-amber-400"
                >
                  Nạp thêm →
                </button>
              </div>
            ) : null}
            <AnimatePresence>
              {hasTikTokUrl ? (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.12 }}
                  className="mb-2"
                >
                  <URLChip url={message} />
                </motion.div>
              ) : null}
            </AnimatePresence>
            <div
              className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-alt)]"
              style={{ boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)" }}
            >
              <div className="px-4 pb-1 pt-3">
                <textarea
                  ref={textareaRef}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Dán link TikTok hoặc hỏi bất cứ thứ gì..."
                  rows={1}
                  maxLength={charLimit + 50}
                  disabled={inputDisabled}
                  className="w-full resize-none overflow-hidden border-none bg-transparent leading-relaxed text-[var(--ink)] outline-none placeholder:text-[var(--faint)] disabled:opacity-50"
                  style={{ minHeight: "36px", fontSize: "16px", lineHeight: "1.5" }}
                />
              </div>
              <div className="flex items-center justify-end px-3 pb-3">
                <div className="flex items-center gap-2">
                  {charCount > 0 ? (
                    <span
                      className={`font-mono text-xs tabular-nums ${
                        charOverLimit ? "text-[var(--danger)]" : "text-[var(--faint)]"
                      }`}
                    >
                      {charCount}/{charLimit}
                    </span>
                  ) : null}
                  <button
                    type="button"
                    disabled={!message.trim() || charOverLimit || inputDisabled}
                    onClick={() => void handleSend()}
                    className="flex h-8 w-8 items-center justify-center rounded-full transition-all duration-[120ms] active:scale-95"
                    style={{
                      background:
                        message.trim() && !charOverLimit && !inputDisabled ? "var(--gradient-primary)" : "var(--faint)",
                      cursor: !message.trim() || charOverLimit || inputDisabled ? "not-allowed" : "pointer",
                    }}
                  >
                    <ArrowUp className="h-4 w-4 text-white" strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            </div>
            {/* Time estimate hint — shown for video/competitor intents */}
            {hasTikTokUrl && !inputDisabled ? (
              <p className="mt-1.5 text-center text-[10px] text-[var(--faint)]">
                Phân tích sâu cần 30 giây – 2 phút
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
