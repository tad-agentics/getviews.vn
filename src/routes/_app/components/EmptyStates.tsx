/**
 * EmptyStates — module-level components for the chat empty screen.
 *
 * Defined outside ChatScreen so React never unmounts/remounts them on
 * parent re-renders (e.g. keystroke in the message textarea). Memoized
 * so they only re-render when their own props change.
 *
 * motion animations use `initial` only on first mount. Because these
 * components are stable across parent re-renders they will not re-fire.
 */
import { memo, useState, useRef, useEffect, type ElementType } from "react";
import { motion } from "motion/react";
import { useNavigate } from "react-router";
import { ArrowUp, Database, BarChart2, Search, TrendingUp, Video } from "lucide-react";
import { PromptCards } from "@/routes/_app/components/PromptCards";
import { QuickActionModal } from "@/routes/_app/components/QuickActionModal";
import { NicheSelector } from "@/routes/_app/components/NicheSelector";
import { MorningRitualBanner } from "@/routes/_app/components/MorningRitualBanner";

export { QuickActionModal } from "@/routes/_app/components/QuickActionModal";

/* ─── Quick action config ─────────────────────────────────────────────── */
type QuickActionModalKey = "soi-kenh" | "xu-huong" | "kich-ban" | "tim-kol" | "tu-van";

type QuickAction =
  | {
      text: string;
      subtext: string;
      Icon: ElementType;
      isFree: boolean;
      modalKey: QuickActionModalKey;
    }
  | {
      text: string;
      subtext: string;
      Icon: ElementType;
      isFree: boolean;
      href: "/app/video";
    };

const QUICK_ACTIONS: QuickAction[] = [
  {
    text: "Soi Video",
    subtext: "Dán link TikTok — phân tích hook, nhịp, CTA",
    Icon: Video,
    href: "/app/video",
    isFree: false,
  },
  {
    text: "Soi Kênh Đối Thủ",
    subtext: "Dán @handle — xem công thức content của họ",
    Icon: Search,
    modalKey: "soi-kenh",
    isFree: false,
  },
  {
    text: "Xu Hướng Tuần Này",
    subtext: "Hook nào đang chạy trong ngách của bạn",
    Icon: TrendingUp,
    modalKey: "xu-huong",
    isFree: true,
  },
  {
    text: "Lên Kịch Bản Quay",
    subtext: "Từ chủ đề → shot list sẵn sàng quay",
    Icon: Video,
    modalKey: "kich-ban",
    isFree: false,
  },
  {
    text: "Tìm KOL / Creator",
    subtext: "Gợi ý tài khoản đáng theo dõi hoặc hợp tác",
    Icon: Search,
    modalKey: "tim-kol",
    isFree: true,
  },
  {
    text: "Tư Vấn Content",
    subtext: "Hướng nội dung + format phù hợp ngách",
    Icon: BarChart2,
    modalKey: "tu-van",
    isFree: false,
  },
];

/* ─── MobileEmptyState ────────────────────────────────────────────────── */
export const MobileEmptyState = memo(function MobileEmptyState({
  nicheLabel,
  onSelectPrompt,
}: {
  nicheLabel: string;
  onSelectPrompt: (p: string) => void;
}) {
  const navigate = useNavigate();
  const [activeModal, setActiveModal] = useState<string | null>(null);

  const handleModalContinue = (prompt: string) => {
    setActiveModal(null);
    onSelectPrompt(prompt);
  };

  const openQuickAction = (action: QuickAction) => {
    if ("href" in action) navigate(action.href);
    else setActiveModal(action.modalKey);
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
        <div className="mt-2 w-full">
          <MorningRitualBanner nicheLabel={nicheLabel} onSelectPrompt={onSelectPrompt} />
        </div>
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: 0.05, ease: "easeOut" }}
          className="mt-4 w-full"
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
                  onClick={() => openQuickAction(action)}
                  className="group flex flex-col gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-left transition-all duration-[120ms] hover:border-[var(--border-active)] hover:shadow-sm active:scale-[0.98]"
                >
                  <Icon
                    className="h-4 w-4 text-[var(--muted)] transition-colors duration-[120ms] group-hover:text-[var(--ink)]"
                    strokeWidth={1.5}
                  />
                  <p className="text-xs font-semibold leading-snug text-[var(--ink)]">{action.text}</p>
                  <p className="text-[10px] leading-tight text-[var(--muted)]">{action.subtext}</p>
                </motion.button>
              );
            })}
          </div>
        </motion.div>
      </div>
    </>
  );
});

/* ─── DesktopCenteredEmpty ────────────────────────────────────────────── */
/**
 * Owns its own textarea state — does NOT receive message/setMessage from
 * ChatScreen. This prevents ChatScreen's message state from causing
 * this component to re-render (and re-fire motion animations) on every
 * keystroke. When the user sends, `onSend(text)` passes the value up.
 */
export const DesktopCenteredEmpty = memo(function DesktopCenteredEmpty({
  nicheLabel,
  initialValue,
  inputDisabled,
  needsNiche,
  userId,
  onSend,
}: {
  nicheLabel: string;
  initialValue: string;
  inputDisabled: boolean;
  needsNiche: boolean;
  userId: string | undefined;
  onSend: (text: string) => void;
}) {
  const navigate = useNavigate();
  const [msg, setMsg] = useState(initialValue);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const charLimit = 1000;
  const charCount = msg.length;
  const charOverLimit = charCount > charLimit;

  // Sync if parent pushes a prefill after mount (e.g. "Phân tích video này" button)
  useEffect(() => {
    if (initialValue && !msg) setMsg(initialValue);
  }, [initialValue]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [msg]);

  const handleSend = () => {
    if (!msg.trim() || charOverLimit || inputDisabled) return;
    onSend(msg);
    setMsg("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleModalContinue = (prompt: string) => {
    setActiveModal(null);
    onSend(prompt);
  };

  const openQuickAction = (action: QuickAction) => {
    if ("href" in action) navigate(action.href);
    else setActiveModal(action.modalKey);
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
          {needsNiche && userId ? (
            <div className="mb-6">
              <NicheSelector userId={userId} />
            </div>
          ) : null}

          <div
            className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]"
            style={{ boxShadow: "0 1px 4px 0 rgba(0,0,0,0.06)" }}
          >
            <div className="px-4 pb-2 pt-4">
              <textarea
                ref={textareaRef}
                value={msg}
                onChange={(e) => setMsg(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={nicheLabel ? `Hỏi về hook, trend, hay kênh ${nicheLabel}...` : "Hỏi về xu hướng TikTok, hook, video..."}
                rows={3}
                maxLength={charLimit + 50}
                className="w-full resize-none overflow-hidden border-none bg-transparent text-sm leading-relaxed text-[var(--ink)] outline-none placeholder:text-[var(--faint)]"
                style={{ minHeight: 72, fontSize: 14 }}
              />
            </div>

            <div className="flex items-center justify-end gap-2 px-3 pb-3">
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
                disabled={!msg.trim() || charOverLimit || inputDisabled}
                onClick={handleSend}
                className="flex h-8 w-8 items-center justify-center rounded-full transition-all duration-[120ms] active:scale-95"
                style={{
                  background: msg.trim() && !charOverLimit && !inputDisabled ? "var(--gradient-primary)" : "var(--faint)",
                  cursor: !msg.trim() || charOverLimit || inputDisabled ? "not-allowed" : "pointer",
                }}
              >
                <ArrowUp className="h-4 w-4 text-white" strokeWidth={2.5} />
              </button>
            </div>

            <div className="flex items-center border-t border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
              <div className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
                <Database className="h-3 w-3" strokeWidth={1.6} />
                <span className="font-mono">46.000+ video</span>
              </div>
            </div>
          </div>

          <div className="mt-3">
            <MorningRitualBanner nicheLabel={nicheLabel} onSelectPrompt={(p) => { setMsg(p); }} />
          </div>

          <div className="mt-6">
            <PromptCards nicheLabel={nicheLabel} onSelect={(p) => { setMsg(p); }} />
          </div>

          <div className="mt-6">
            <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Thao tác nhanh</p>
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
              {QUICK_ACTIONS.map((action, idx) => {
                const Icon = action.Icon;
                return (
                  <motion.button
                    key={idx}
                    type="button"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18, delay: 0.1 + idx * 0.05, ease: "easeOut" }}
                    onClick={() => openQuickAction(action)}
                    className="group flex flex-col gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-left transition-all duration-[120ms] hover:border-[var(--border-active)] hover:shadow-sm active:scale-[0.98]"
                  >
                    <Icon
                      className="h-4 w-4 text-[var(--muted)] transition-colors duration-[120ms] group-hover:text-[var(--ink)]"
                      strokeWidth={1.5}
                    />
                    <p className="text-xs font-semibold leading-snug text-[var(--ink)]">{action.text}</p>
                    <p className="text-[10px] leading-tight text-[var(--muted)]">{action.subtext}</p>
                  </motion.button>
                );
              })}
            </div>
          </div>
        </motion.div>
      </div>
    </>
  );
});
