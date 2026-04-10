import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
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
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { DiagnosisRow, type DiagnosisRowData } from "@/routes/_app/components/DiagnosisRow";
import { ThumbnailStrip, type ThumbnailItem } from "@/routes/_app/components/ThumbnailStrip";
import { CopyButton } from "@/routes/_app/components/CopyButton";
import { URLChip } from "@/routes/_app/components/URLChip";
import { PromptCards } from "@/routes/_app/components/PromptCards";
import { StreamingStatusText } from "@/routes/_app/components/StreamingStatusText";
import { FreeQueryPill } from "@/routes/_app/components/FreeQueryPill";
import { NicheSelector } from "@/routes/_app/components/NicheSelector";
import { HookRankingBar } from "@/routes/_app/components/HookRankingBar";
import { BriefBlock } from "@/routes/_app/components/BriefBlock";
import { CreatorCard } from "@/routes/_app/components/CreatorCard";

/* ─── Quick action cards (Make) ───────────────────────────────────────── */
interface QuickAction {
  text: string;
  Icon: React.ElementType;
  modalKey: "marketing" | "tiktok-page" | "trends" | "video";
}

const QUICK_ACTIONS: QuickAction[] = [
  { text: "Tư vấn chiến lược marketing", Icon: BarChart2, modalKey: "marketing" },
  { text: "Phân tích trang TikTok", Icon: Search, modalKey: "tiktok-page" },
  { text: "Tìm xu hướng mới nhất", Icon: TrendingUp, modalKey: "trends" },
  { text: "Chẩn đoán video cụ thể", Icon: Video, modalKey: "video" },
];

interface ModalConfig {
  title: string;
  fields: {
    label: string;
    placeholder: string;
    type: "input" | "textarea";
    key: string;
  }[];
  buildPrompt: (values: Record<string, string>) => string;
}

const MODAL_CONFIGS: Record<string, ModalConfig> = {
  marketing: {
    title: "Chiến lược Marketing",
    fields: [
      { label: "Tên sản phẩm của bạn là gì?", placeholder: "VD: FitTrack", type: "input", key: "product" },
      {
        label: "Mô tả sản phẩm",
        placeholder: "VD: Ứng dụng fitness AI tạo kế hoạch tập luyện cá nhân hóa",
        type: "textarea",
        key: "description",
      },
    ],
    buildPrompt: (v) => `Tư vấn chiến lược marketing TikTok cho sản phẩm "${v.product}": ${v.description}`,
  },
  "tiktok-page": {
    title: "Phân tích trang TikTok",
    fields: [
      { label: "TikTok profile URL", placeholder: "https://www.tiktok.com/@username", type: "input", key: "url" },
    ],
    buildPrompt: (v) => `Phân tích trang TikTok: ${v.url}`,
  },
  trends: {
    title: "Tìm xu hướng mới nhất",
    fields: [
      { label: "Xu hướng trong lĩnh vực nào?", placeholder: "VD: fitness, skincare, AI tools", type: "input", key: "niche" },
    ],
    buildPrompt: (v) => `Tìm xu hướng TikTok mới nhất trong lĩnh vực: ${v.niche}`,
  },
  video: {
    title: "Chẩn đoán video",
    fields: [
      { label: "TikTok video URL", placeholder: "https://www.tiktok.com/@username/video/...", type: "input", key: "url" },
    ],
    buildPrompt: (v) => `Chẩn đoán video TikTok: ${v.url}`,
  },
};

function QuickActionModal({
  modalKey,
  onClose,
  onContinue,
}: {
  modalKey: string;
  onClose: () => void;
  onContinue: (prompt: string) => void;
}) {
  const config = MODAL_CONFIGS[modalKey];
  const [values, setValues] = useState<Record<string, string>>(
    () => Object.fromEntries(config.fields.map((f) => [f.key, ""])),
  );

  const allFilled = config.fields.every((f) => values[f.key]?.trim());

  const handleContinue = () => {
    if (!allFilled) return;
    onContinue(config.buildPrompt(values));
  };

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          key="modal"
          initial={{ opacity: 0, scale: 0.95, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 8 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="relative flex w-full max-w-[420px] flex-col gap-5 rounded-2xl p-6"
          style={{
            background: "var(--surface)",
            boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full text-[var(--muted)] transition-colors duration-[120ms] hover:bg-[var(--surface-alt)] hover:text-[var(--ink)]"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>

          <h2 className="pr-8 text-[var(--ink)]" style={{ fontSize: "1.35rem", fontWeight: 800, lineHeight: 1.2 }}>
            {config.title}
          </h2>

          <div className="flex flex-col gap-4">
            {config.fields.map((field) => (
              <div key={field.key} className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-[var(--ink)]">{field.label}</label>
                {field.type === "input" ? (
                  <input
                    type="text"
                    placeholder={field.placeholder}
                    value={values[field.key]}
                    onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleContinue();
                    }}
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm text-[var(--ink)] transition-all duration-[120ms] placeholder:text-[var(--faint)] focus:border-[var(--purple)] focus:outline-none focus:ring-1 focus:ring-[var(--purple)]"
                    autoFocus={field.key === config.fields[0].key}
                  />
                ) : (
                  <textarea
                    placeholder={field.placeholder}
                    value={values[field.key]}
                    onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                    rows={3}
                    className="w-full resize-none rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm text-[var(--ink)] transition-all duration-[120ms] placeholder:text-[var(--faint)] focus:border-[var(--purple)] focus:outline-none focus:ring-1 focus:ring-[var(--purple)]"
                  />
                )}
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleContinue}
            disabled={!allFilled}
            className="h-12 w-full rounded-xl text-sm font-semibold text-white transition-all duration-[120ms] active:scale-[0.98]"
            style={{
              background: allFilled ? "var(--gradient-primary)" : "var(--faint)",
              cursor: allFilled ? "pointer" : "not-allowed",
            }}
          >
            Tiếp tục
          </button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

type ChatMsg = {
  id: string;
  role: string;
  content: string | null;
  intent_type?: string | null;
  is_free?: boolean | null;
};

function isResumeQuery(q: string): boolean {
  const s = q.trim().toLowerCase();
  return ["tiếp", "tiếp tục", "continue", "resume", "/tiếp"].includes(s);
}

function detectIntent(query: string, priorAssistant: boolean): { intentType: string; isFree: boolean } {
  const q = query.trim();
  const ql = q.toLowerCase();

  if (/https?:\/\/[^\s]*tiktok\.com/i.test(q)) {
    if (/\/video\//i.test(q)) return { intentType: "video_diagnosis", isFree: false };
    return { intentType: "competitor_profile", isFree: false };
  }
  if (/@\w/.test(q)) return { intentType: "competitor_profile", isFree: false };
  if (/\b(hot|trending|xu hướng|đang lên)\b/i.test(ql)) return { intentType: "trend_spike", isFree: true };
  if (/\b(tìm kol|tìm creator|\bkol\b)\b/i.test(ql)) return { intentType: "find_creators", isFree: true };
  if (priorAssistant) return { intentType: "follow_up", isFree: true };
  return { intentType: "brief_generation", isFree: false };
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
        <p className="whitespace-pre-wrap text-sm text-[var(--ink)]">{parsed.plain}</p>
      ) : null}
    </>
  );
}

export default function ChatScreen() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlSessionId = searchParams.get("session");
  const [sessionId, setSessionId] = useState<string | null>(urlSessionId);

  useEffect(() => {
    const s = searchParams.get("session");
    if (s) setSessionId(s);
  }, [searchParams]);

  const { data: profile } = useProfile();
  const { data: sessionRow, refetch: refetchSession } = useChatSession(sessionId);
  const createSession = useCreateSession();
  const insertUser = useInsertUserMessage();
  const { status, text, streamId, lastSeq, error, stream, reset } = useChatStream();
  const { data: nicheRows } = useNicheTaxonomy();

  const messages = useMemo(
    () => (sessionRow?.chat_messages ?? []) as unknown as ChatMsg[],
    [sessionRow],
  );

  const nicheLabel = useMemo(() => {
    const pn = profile?.primary_niche;
    if (pn == null || pn === "") return "";
    const id = typeof pn === "number" ? pn : Number(pn);
    if (!Number.isNaN(id) && nicheRows?.length) {
      return nicheRows.find((n) => n.id === id)?.name ?? "";
    }
    return String(pn);
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

  useEffect(() => {
    if (messages.length > 0) setShowMessages(true);
  }, [messages.length]);

  const credits = profile?.deep_credits_remaining ?? 0;
  const processing = Boolean(profile?.is_processing);
  const needsNiche = profile?.primary_niche == null || profile?.primary_niche === "";

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
      if (needsNiche) return;

      setClientPaywall(false);

      const isResume = Boolean(resume && lastIntentRef.current);
      const { intentType, isFree } = isResume
        ? { intentType: lastIntentRef.current!, isFree: true }
        : detectIntent(trimmed, priorAssistant);

      if (!isFree && credits <= 0) {
        setClientPaywall(true);
        return;
      }

      setShowMessages(true);

      let sid = sessionId;
      if (!sid) {
        const rawNiche = profile?.primary_niche;
        const nicheIdNum =
          rawNiche != null && rawNiche !== "" ? Number.parseInt(String(rawNiche), 10) : Number.NaN;
        const row = await createSession.mutateAsync({
          userId: user.id,
          nicheId: Number.isFinite(nicheIdNum) ? nicheIdNum : null,
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
      needsNiche,
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

  const handleSend = async () => {
    if (!message.trim() || charOverLimit) return;
    const q = message;
    const trimmed = q.trim();
    const resumePayload =
      isResumeQuery(trimmed) &&
      status === "error" &&
      streamId !== null &&
      error !== "insufficient_credits" &&
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

  const inputDisabled = processing || needsNiche || insertUser.isPending || status === "streaming";

  /* ─── Desktop empty (Make + PromptCards) ──────────────────────────── */
  function DesktopCenteredEmpty({
    message: msg,
    setMessage: setMsg,
    onSend,
  }: {
    message: string;
    setMessage: (v: string) => void;
    onSend: () => void;
  }) {
    const textareaRefInner = useRef<HTMLTextAreaElement>(null);
    const charCountInner = msg.length;
    const charLimitInner = 1000;
    const charOverLimitInner = charCountInner > charLimitInner;
    const [activeModal, setActiveModal] = useState<string | null>(null);

    useEffect(() => {
      const el = textareaRefInner.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }, [msg]);

    const handleKeyDownInner = (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSend();
      }
    };

    const handleModalContinue = (prompt: string) => {
      setActiveModal(null);
      setMsg(prompt);
      onSend();
    };

    return (
      <>
        {activeModal ? (
          <QuickActionModal
            modalKey={activeModal}
            onClose={() => setActiveModal(null)}
            onContinue={handleModalContinue}
          />
        ) : null}

        <div className="flex flex-1 flex-col items-center justify-center px-6 pb-10">
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="mb-4 text-center text-[1.75rem] font-extrabold gradient-text"
          >
            Sẵn sàng phân tích content của bạn.
          </motion.h1>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.05, ease: "easeOut" }}
            className="w-full"
            style={{ maxWidth: 600 }}
          >
            <p className="mb-2 text-center text-xs text-[var(--muted)]">Thử gợi ý hoặc nhập câu hỏi</p>
            <PromptCards nicheLabel={nicheLabel} onSelect={(p) => setMsg(p)} />

            <div
              className="mt-6 overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]"
              style={{ boxShadow: "0 1px 4px 0 rgba(0,0,0,0.06)" }}
            >
              <div className="px-4 pb-2 pt-4">
                <textarea
                  ref={textareaRefInner}
                  value={msg}
                  onChange={(e) => setMsg(e.target.value)}
                  onKeyDown={handleKeyDownInner}
                  placeholder="Hỏi về xu hướng TikTok, hook, video..."
                  rows={2}
                  maxLength={charLimitInner + 50}
                  className="w-full resize-none overflow-hidden border-none bg-transparent text-sm leading-relaxed text-[var(--ink)] outline-none placeholder:text-[var(--faint)]"
                  style={{ minHeight: 52, fontSize: 14 }}
                />
              </div>

              <div className="flex items-center justify-end gap-2 px-3 pb-3">
                {charCountInner > 0 ? (
                  <span
                    className={`font-mono text-xs tabular-nums ${
                      charOverLimitInner ? "text-[var(--danger)]" : "text-[var(--faint)]"
                    }`}
                  >
                    {charCountInner}/{charLimitInner}
                  </span>
                ) : null}
                <button
                  type="button"
                  disabled={!msg.trim() || charOverLimitInner || inputDisabled}
                  onClick={onSend}
                  className="flex h-8 w-8 items-center justify-center rounded-full transition-all duration-[120ms] active:scale-95"
                  style={{
                    background: msg.trim() && !charOverLimitInner && !inputDisabled ? "var(--gradient-primary)" : "var(--faint)",
                    cursor: !msg.trim() || charOverLimitInner || inputDisabled ? "not-allowed" : "pointer",
                  }}
                >
                  <ArrowUp className="h-4 w-4 text-white" strokeWidth={2.5} />
                </button>
              </div>

              <div className="flex items-center justify-between border-t border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
                <div className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
                  <Database className="h-3 w-3" strokeWidth={1.6} />
                  <span className="font-mono">46.000+ video</span>
                </div>
                <svg className="h-5 w-5 flex-shrink-0" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path
                    fill="#69C9D0"
                    d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"
                  />
                  <path
                    fill="#EE1D52"
                    d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"
                  />
                  <path
                    fill="#ffffff"
                    d="M18.58 6.09a4.83 4.83 0 0 1-3.77-4.25V1.36h-3.45v13.31a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V7.97a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V7.9a8.18 8.18 0 0 0 4.78 1.52V6.05a4.85 4.85 0 0 1-1.01.04z"
                  />
                </svg>
              </div>
            </div>

            <div className="mt-6">
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Thao tác nhanh</p>
              <div className="grid grid-cols-2 gap-2.5">
                {QUICK_ACTIONS.map((action, idx) => {
                  const Icon = action.Icon;
                  return (
                    <motion.button
                      key={idx}
                      type="button"
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.18, delay: 0.1 + idx * 0.05, ease: "easeOut" }}
                      onClick={() => setActiveModal(action.modalKey)}
                      className="group flex flex-col gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-left transition-all duration-[120ms] hover:border-[var(--border-active)] hover:shadow-sm active:scale-[0.98]"
                    >
                      <Icon
                        className="h-4 w-4 text-[var(--muted)] transition-colors duration-[120ms] group-hover:text-[var(--ink)]"
                        strokeWidth={1.5}
                      />
                      <p className="text-xs leading-snug text-[var(--ink)]">{action.text}</p>
                    </motion.button>
                  );
                })}
              </div>
            </div>
          </motion.div>
        </div>
      </>
    );
  }

  function DesktopInput({
    message: msg,
    setMessage: setMsg,
    onSend,
  }: {
    message: string;
    setMessage: (v: string) => void;
    onSend: () => void;
  }) {
    const textareaRefInner = useRef<HTMLTextAreaElement>(null);
    const charCountInner = msg.length;
    const charLimitInner = 1000;
    const charOverLimitInner = charCountInner > charLimitInner;

    useEffect(() => {
      const el = textareaRefInner.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }, [msg]);

    const handleKeyDownInner = (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSend();
      }
    };

    return (
      <div className="flex-shrink-0 px-10 pb-7">
        {needsNiche && user?.id ? (
          <div className="mb-4">
            <NicheSelector userId={user.id} />
          </div>
        ) : null}
        <div
          className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]"
          style={{ boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)" }}
        >
          <div className="px-4 pb-2 pt-4">
            <textarea
              ref={textareaRefInner}
              value={msg}
              onChange={(e) => setMsg(e.target.value)}
              onKeyDown={handleKeyDownInner}
              placeholder="Dán link TikTok hoặc hỏi bất cứ thứ gì..."
              rows={1}
              maxLength={charLimitInner + 50}
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
              {charCountInner > 0 ? (
                <span
                  className={`font-mono text-xs tabular-nums ${
                    charOverLimitInner ? "text-[var(--danger)]" : "text-[var(--faint)]"
                  }`}
                >
                  {charCountInner}/{charLimitInner}
                </span>
              ) : null}
              <button
                type="button"
                disabled={!msg.trim() || charOverLimitInner || inputDisabled}
                onClick={onSend}
                className="flex h-8 w-8 items-center justify-center rounded-full transition-all duration-[120ms] active:scale-95"
                style={{
                  background: msg.trim() && !charOverLimitInner && !inputDisabled ? "var(--gradient-primary)" : "var(--faint)",
                  cursor: !msg.trim() || charOverLimitInner || inputDisabled ? "not-allowed" : "pointer",
                }}
              >
                <ArrowUp className="h-4 w-4 text-white" strokeWidth={2.5} />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  function MobileEmptyState({ onSelectPrompt }: { onSelectPrompt: (p: string) => void }) {
    const [activeModal, setActiveModal] = useState<string | null>(null);

    const handleModalContinue = (prompt: string) => {
      setActiveModal(null);
      onSelectPrompt(prompt);
    };

    return (
      <>
        {activeModal ? (
          <QuickActionModal
            modalKey={activeModal}
            onClose={() => setActiveModal(null)}
            onContinue={handleModalContinue}
          />
        ) : null}
        <div className="flex flex-1 flex-col items-center px-5 pb-4 pt-16">
          <motion.h1
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="gradient-text mb-4 text-center"
            style={{ fontWeight: 800, fontSize: "1.5rem", lineHeight: 1.25 }}
          >
            Sẵn sàng phân tích content của bạn.
          </motion.h1>
          <p className="mb-2 text-center text-xs text-[var(--muted)]">Chọn gợi ý hoặc thao tác nhanh</p>
          <PromptCards nicheLabel={nicheLabel} onSelect={onSelectPrompt} />

          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: 0.05, ease: "easeOut" }}
            className="mt-6 w-full"
          >
            <p className="mb-2.5 text-center text-xs font-semibold uppercase tracking-widest text-[var(--faint)]">
              Thao tác nhanh
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              {QUICK_ACTIONS.map((action, idx) => {
                const Icon = action.Icon;
                return (
                  <motion.button
                    key={idx}
                    type="button"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18, delay: 0.1 + idx * 0.05, ease: "easeOut" }}
                    onClick={() => setActiveModal(action.modalKey)}
                    className="group flex flex-col gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-left transition-all duration-[120ms] hover:border-[var(--border-active)] hover:shadow-sm active:scale-[0.98]"
                  >
                    <Icon
                      className="h-4 w-4 text-[var(--muted)] transition-colors duration-[120ms] group-hover:text-[var(--ink)]"
                      strokeWidth={1.5}
                    />
                    <p className="text-xs leading-snug text-[var(--ink)]">{action.text}</p>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        </div>
      </>
    );
  }

  const paywallVisible = clientPaywall || error === "insufficient_credits";

  const inFlightVisible =
    status === "streaming" ||
    (status === "error" && streamId !== null && error !== "insufficient_credits");

  const messageThread = (
    <div className="space-y-4">
      {paywallVisible ? (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="mb-3 text-sm text-[var(--ink)]">
            Hết deep credit tháng này. Mua thêm 10 credit = 130.000 VND.
          </p>
          <Link
            to="/app/pricing"
            className="inline-flex text-sm font-semibold text-[var(--purple)] hover:underline"
          >
            Mua credit →
          </Link>
        </div>
      ) : null}

      {messages.map((m) => {
        if (m.role === "user") {
          return (
            <div key={m.id} className="flex justify-end">
              <div className="flex max-w-[80%] items-start gap-2 rounded-xl bg-[var(--purple-light)] px-4 py-3 lg:max-w-[75%]">
                <p className="text-sm text-[var(--ink)]">{m.content}</p>
                {m.is_free && m.id === lastUser?.id ? <FreeQueryPill pulseKey={freePillKey} /> : null}
              </div>
            </div>
          );
        }
        if (m.role === "assistant") {
          const parsed = parseAssistantPayload(m.content);
          const hasBody =
            parsed &&
            (parsed.plain ||
              (parsed.diagnosis_rows && parsed.diagnosis_rows.length > 0) ||
              (parsed.hook_ranking && parsed.hook_ranking.length > 0) ||
              (parsed.brief_sections && parsed.brief_sections.length > 0) ||
              (parsed.creators && parsed.creators.length > 0) ||
              parsed.error_video);
          if (!hasBody) return null;
          return (
            <div key={m.id} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 lg:p-5">
              <AssistantStructuredBlock parsed={parsed} />
            </div>
          );
        }
        return null;
      })}

      {inFlightVisible ? (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 lg:p-5">
          <StreamingStatusText
            phase={status === "streaming" ? "streaming" : "idle"}
            isVideoIntent={VIDEO_INTENTS.has(lastStreamIntent ?? "")}
          />
          {status === "streaming" ? (
            <div className="mt-3 space-y-2 animate-pulse">
              <div className="h-3 w-[75%] rounded bg-[var(--border)]" />
              <div className="h-3 w-[50%] rounded bg-[var(--border)]" />
              <div className="h-3 w-[66%] rounded bg-[var(--border)]" />
            </div>
          ) : null}
          {status === "error" && streamId !== null && error !== "insufficient_credits" ? (
            <p className="mt-2 text-sm text-[var(--muted)]">— Bị gián đoạn. Gõ &apos;tiếp&apos; để tiếp tục.</p>
          ) : null}
          {text ? <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--ink)]">{text}</p> : null}
        </div>
      ) : null}

      <div ref={messagesEndRef} />
    </div>
  );

  return (
    <AppLayout active="chat" enableMobileSidebar>
      <div className="hidden h-full flex-col lg:flex">
        {!showMessages ? (
          <DesktopCenteredEmpty message={message} setMessage={setMessage} onSend={() => void handleSend()} />
        ) : (
          <>
            <div className="flex-1 space-y-4 overflow-y-auto px-10 py-6">{messageThread}</div>
            <DesktopInput message={message} setMessage={setMessage} onSend={() => void handleSend()} />
          </>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:hidden">
        <div className="flex-1 overflow-y-auto bg-[var(--surface-alt)]">
          {!showMessages ? (
            <MobileEmptyState
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
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
