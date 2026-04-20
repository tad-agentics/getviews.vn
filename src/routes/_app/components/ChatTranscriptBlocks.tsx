/**
 * Shared assistant payload parsing + structured blocks for legacy chat transcripts
 * (read-only history). Extracted from the former ChatScreen (Phase C.7).
 */
import { DiagnosisRow, type DiagnosisRowData } from "@/routes/_app/components/DiagnosisRow";
import { ThumbnailStrip, type ThumbnailItem } from "@/routes/_app/components/ThumbnailStrip";
import { CopyButton } from "@/routes/_app/components/CopyButton";
import { HookRankingBar } from "@/routes/_app/components/HookRankingBar";
import { BriefBlock } from "@/routes/_app/components/BriefBlock";
import { MarkdownRenderer } from "@/components/chat/MarkdownRenderer";

export type ParsedAssistant = {
  diagnosis_rows?: DiagnosisRowData[];
  corpus_cite?: { count: number; niche: string; timeframe: string; updated_hours_ago?: number };
  thumbnails?: ThumbnailItem[];
  hook_ranking?: { label: string; percent: number }[];
  brief_sections?: string[];
  creators?: { handle: string; meta: string }[];
  error_video?: boolean;
  plain?: string;
};

export function parseAssistantPayload(content: string | null): ParsedAssistant | null {
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

function buildCopyPlain(parsed: ParsedAssistant | null): string {
  if (parsed?.plain) return parsed.plain;
  const rows = parsed?.diagnosis_rows ?? [];
  if (rows.length) return rows.map((d) => `${d.type === "fail" ? "✕" : "✓"} ${d.finding}`).join("\n");
  return "";
}

export function AssistantStructuredBlock({ parsed }: { parsed: ParsedAssistant | null }) {
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
            <div
              key={i}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3"
            >
              <p className="font-semibold text-[var(--ink)]">{c.handle}</p>
              <p className="text-xs text-[var(--muted)]">{c.meta}</p>
            </div>
          ))}
        </div>
      ) : null}
      {parsed.plain && !diagnosis.length ? (
        <MarkdownRenderer text={parsed.plain} />
      ) : null}
    </>
  );
}
