import { motion } from "motion/react";
import { MessageCircle, ShoppingBag, HelpCircle } from "lucide-react";

import type { CommentRadarData } from "@/lib/types/corpus-sidecars";

export type { CommentRadarData } from "@/lib/types/corpus-sidecars";

const LANGUAGE_LABEL: Record<CommentRadarData["language"], string> = {
  vi: "Phần lớn tiếng Việt",
  mixed: "Trộn Việt + tiếng khác",
  "non-vi": "Khán giả ngoài Việt Nam",
  unknown: "",
};

function formatVN(n: number): string {
  return n.toLocaleString("vi-VN");
}

/**
 * CommentRadarTile — sentiment split + purchase-intent signal from the
 * video's comment section. Backend populates this on demand for video_diagnosis
 * (see comment_radar_cache.resolve_comment_radar). Rendered above the
 * thumbnail tile when structured_output.comment_radar is present.
 *
 * Sellers read this to gauge "would this audience actually buy my product?"
 * before committing to a KOL. Creators read it to see if their "tôi sẽ mua"
 * signal is landing. Hidden when null (no comments fetched / sparse video).
 */
export function CommentRadarTile({ data }: { data: CommentRadarData }) {
  if (!data || data.sampled === 0) return null;

  const { sentiment, purchase_intent, questions_asked, sampled, total_available } = data;
  const pos = Math.max(0, Math.min(100, sentiment.positive_pct));
  const neg = Math.max(0, Math.min(100, sentiment.negative_pct));
  const neu = Math.max(0, 100 - pos - neg);

  const langLabel = LANGUAGE_LABEL[data.language] || "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="my-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3"
    >
      <div className="flex items-center gap-2 text-xs">
        <MessageCircle className="h-3.5 w-3.5 text-[var(--muted)]" strokeWidth={2} />
        <p className="font-semibold text-[var(--ink)]">
          Bình luận
          <span className="ml-1.5 font-normal text-[var(--muted)]">
            ({formatVN(sampled)}
            {total_available > sampled ? ` / ~${formatVN(total_available)}` : ""})
          </span>
        </p>
      </div>

      {/* Sentiment bar — single 4px bar split into 3 segments */}
      <div className="mt-2 flex h-1.5 w-full overflow-hidden rounded-full bg-[var(--border)]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pos}%` }}
          transition={{ duration: 0.4, delay: 0.05, ease: "easeOut" }}
          className="bg-emerald-500"
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${neu}%` }}
          transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" }}
          className="bg-slate-400"
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${neg}%` }}
          transition={{ duration: 0.4, delay: 0.15, ease: "easeOut" }}
          className="bg-rose-500"
        />
      </div>

      <p className="mt-1.5 text-[11px] text-[var(--muted)]">
        <span className="text-emerald-600">{pos.toFixed(0)}% tích cực</span>
        {" · "}
        <span className="text-[var(--muted)]">{neu.toFixed(0)}% trung tính</span>
        {" · "}
        <span className="text-rose-600">{neg.toFixed(0)}% tiêu cực</span>
      </p>

      {/* Purchase intent — the seller's headline signal */}
      {purchase_intent.count > 0 ? (
        <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 p-2.5 dark:border-emerald-900/40 dark:bg-emerald-950/30">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
            <ShoppingBag className="h-3.5 w-3.5" strokeWidth={2.2} />
            {formatVN(purchase_intent.count)} bình luận có ý định mua
          </div>
          {purchase_intent.top_phrases.length > 0 ? (
            <ul className="mt-1.5 space-y-0.5">
              {purchase_intent.top_phrases.slice(0, 3).map((phrase, i) => (
                <li
                  key={i}
                  className="text-[11px] italic text-[var(--ink)] before:mr-1 before:text-[var(--faint)] before:content-['“'] after:text-[var(--faint)] after:content-['”']"
                >
                  {phrase}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {/* Footer — questions + language */}
      {(questions_asked > 0 || langLabel) ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[var(--muted)]">
          {questions_asked > 0 ? (
            <span className="inline-flex items-center gap-1">
              <HelpCircle className="h-3 w-3" strokeWidth={2} />
              {formatVN(questions_asked)} câu hỏi
            </span>
          ) : null}
          {langLabel ? <span>{langLabel}</span> : null}
        </div>
      ) : null}
    </motion.div>
  );
}
