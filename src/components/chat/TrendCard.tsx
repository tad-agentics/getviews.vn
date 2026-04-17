/**
 * TrendCard — structured UI block for trend_spike responses (P1-6).
 *
 * Rendered when MarkdownRenderer detects a complete trend_card JSON block:
 * {
 *   "type": "trend_card",
 *   "title": "Hook 'Cảnh Báo' + Mặt Người",
 *   "recency": "Mới 3 ngày",
 *   "signal": "rising",           // rising | early | stable | declining
 *   "breakout": "4,2x",           // optional — Vietnamese comma decimal
 *   "videos": ["id1", "id2", "id3"],
 *   "hook_formula": "ĐỪNG [hành động] nếu chưa xem video này",
 *   "mechanism": "Bỏ câu trả lời cliché, tạo comment hỏi thêm",
 *   "corpus_cite": "412 video · tuần này"
 * }
 *
 * D2 animation: 400ms reveal + stagger on children (100ms per section).
 */
import { motion } from "motion/react";
import { SignalBadge } from "./SignalBadge";
import { CopyableBlock } from "./CopyableBlock";
import { hookNameVI } from "@/lib/constants/hook-names-vi";

export interface TrendCardData {
  type: "trend_card";
  title: string;
  recency?: string;
  signal?: string;
  breakout?: string;
  /** Video IDs — kept for schema compatibility but not rendered inline.
   *  Full video_ref blocks with metadata are injected server-side after synthesis. */
  videos?: string[];
  hook_formula?: string;
  mechanism?: string;
  corpus_cite?: string;
  hook_type?: string;
}

interface Props {
  data: TrendCardData;
  index?: number;
}

/** Animated bar that fills from 0 → 100% over 400ms, used as visual divider. */
function BarFill({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      initial={{ scaleX: 0 }}
      animate={{ scaleX: 1 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      className="h-0.5 w-full origin-left rounded-full"
      style={{ background: "var(--gradient-primary)" }}
    />
  );
}

export function TrendCard({ data, index = 0 }: Props) {
  const baseDelay = index * 0.12;

  const titleDisplay = data.hook_type
    ? `${data.title} — ${hookNameVI(data.hook_type)}`
    : data.title;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: baseDelay, ease: "easeOut" }}
      className="my-3 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]"
    >
      {/* Top bar fill — D2 animation */}
      <BarFill delay={baseDelay} />

      <div className="p-4 lg:p-5">
        {/* Header row: title + signal badge + breakout */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25, delay: baseDelay + 0.1 }}
          className="mb-2 flex flex-wrap items-start gap-2"
        >
          <h3
            className="flex-1 text-sm font-bold leading-snug text-[var(--ink)]"
            style={{ minWidth: 0 }}
          >
            {titleDisplay}
          </h3>
          <div className="flex flex-shrink-0 items-center gap-2">
            {data.signal ? <SignalBadge signal={data.signal} size="sm" /> : null}
            {data.breakout ? (
              <span
                className="rounded px-1.5 py-0.5 font-mono text-[10px] font-bold text-[var(--purple)]"
                style={{ background: "var(--purple-light)" }}
              >
                {data.breakout}
              </span>
            ) : null}
          </div>
        </motion.div>

        {/* Recency */}
        {data.recency ? (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, delay: baseDelay + 0.15 }}
            className="mb-3 text-xs text-[var(--muted)]"
          >
            {data.recency}
          </motion.p>
        ) : null}

        {/* Hook formula — copyable block (reuses CopyableBlock from P0-3) */}
        {data.hook_formula ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, delay: baseDelay + 0.25 }}
          >
            <CopyableBlock text={data.hook_formula} />
          </motion.div>
        ) : null}

        {/* "Chạy vì:" mechanism */}
        {data.mechanism ? (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, delay: baseDelay + 0.3 }}
            className="mt-2 text-xs leading-relaxed text-[var(--ink-soft)]"
          >
            <span className="font-semibold text-[var(--ink)]">Chạy vì:</span>{" "}
            {data.mechanism}
          </motion.p>
        ) : null}

        {/* Corpus cite footer */}
        {data.corpus_cite ? (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, delay: baseDelay + 0.35 }}
            className="mt-3 font-mono text-[10px] text-[var(--faint)]"
          >
            {data.corpus_cite}
          </motion.p>
        ) : null}
      </div>
    </motion.div>
  );
}
