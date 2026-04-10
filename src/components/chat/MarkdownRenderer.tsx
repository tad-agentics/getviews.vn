/**
 * MarkdownRenderer — renders synthesis markdown with enriched blocks.
 *
 * Parses the plain text synthesis output from Gemini and upgrades specific
 * patterns into visual components:
 *
 *   1. video_ref JSON blocks  → VideoRefStrip (P0-2)
 *      {"type":"video_ref","video_id":"...","handle":"@x","views":1100000,"days_ago":6}
 *
 *   2. trend_card JSON blocks → TrendCard (P1-6)
 *      {"type":"trend_card","title":"...","signal":"rising","hook_formula":"...","mechanism":"..."}
 *
 *   3. Hook: lines            → CopyableBlock (P0-3)
 *      "Hook: ĐỪNG [hành động] nếu chưa xem video này"
 *      "**Hook:** [Sản phẩm] chỉ [giá] — mua ở đâu?"
 *
 *   4. Markdown formatting     → bold (**text**), headings (##), bullets (-)
 *      (lightweight inline — no full markdown parser dependency)
 *
 * Buffering: JSON blocks are detected as complete objects only,
 * never partially — so incomplete streaming tokens are rendered as plain text
 * until the closing brace arrives and the block is detected on the next render.
 */
import { useMemo } from "react";
import { VideoRefStrip, type VideoRefData } from "./VideoRefStrip";
import { CopyableBlock } from "./CopyableBlock";
import { TrendCard, type TrendCardData } from "./TrendCard";

// ---------------------------------------------------------------------------
// Segment types
// ---------------------------------------------------------------------------

type TextSegment = { kind: "text"; content: string };
type VideoRefSegment = { kind: "video_refs"; refs: VideoRefData[] };
type HookSegment = { kind: "hook"; text: string };
type TrendCardSegment = { kind: "trend_card"; data: TrendCardData; cardIndex: number };

type Segment = TextSegment | VideoRefSegment | HookSegment | TrendCardSegment;

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

const HOOK_LINE_RE = /^\*{0,2}Hook:\*{0,2}\s+(.+)$/;
const VIDEO_REF_RE = /\{"type"\s*:\s*"video_ref"[^}]*\}/g;

/**
 * Match complete trend_card JSON blocks (multi-line-aware).
 * Strategy: find {"type":"trend_card"...} by scanning for balanced braces.
 * This handles nested arrays in the "videos" field.
 */
function extractTrendCards(
  text: string
): { result: string; cards: TrendCardData[] } {
  const cards: TrendCardData[] = [];
  let result = text;
  let searchFrom = 0;

  while (true) {
    const start = result.indexOf('{"type":"trend_card"', searchFrom);
    if (start === -1) break;

    // Walk forward counting braces to find the matching closing }
    let depth = 0;
    let end = -1;
    for (let i = start; i < result.length; i++) {
      if (result[i] === "{") depth++;
      else if (result[i] === "}") {
        depth--;
        if (depth === 0) {
          end = i + 1;
          break;
        }
      }
    }
    if (end === -1) {
      // Incomplete block — leave as plain text, stop scanning
      break;
    }

    const raw = result.slice(start, end);
    try {
      const data = JSON.parse(raw) as TrendCardData;
      if (data.type === "trend_card") {
        const idx = cards.length;
        cards.push(data);
        result =
          result.slice(0, start) +
          `\x00TREND_CARD_${idx}\x00` +
          result.slice(end);
        // restart from same position (marker is shorter than original)
        searchFrom = start + `\x00TREND_CARD_${idx}\x00`.length;
        continue;
      }
    } catch {
      /* malformed — leave as plain text */
    }
    searchFrom = end;
  }

  return { result, cards };
}

function parseSegments(text: string): Segment[] {
  if (!text.trim()) return [];

  // Step 0: extract trend_card blocks first (they may contain video IDs)
  const { result: afterCards, cards: trendCards } = extractTrendCards(text);

  // Step 1: extract all video_ref JSON objects and replace with markers
  const videoRefs: VideoRefData[] = [];
  const indexed: string[] = [];

  const withMarkers = afterCards.replace(VIDEO_REF_RE, (match) => {
    try {
      const data = JSON.parse(match) as VideoRefData;
      if (data.type === "video_ref" && data.video_id) {
        const idx = videoRefs.length;
        videoRefs.push(data);
        indexed.push(match);
        return `\x00VIDEO_REF_${idx}\x00`;
      }
    } catch {
      /* malformed — leave as plain text */
    }
    return match;
  });

  // Step 2: split on both TREND_CARD and VIDEO_REF markers
  // First split on trend card markers
  const COMBINED_MARKER_RE = /\x00(TREND_CARD_\d+|VIDEO_REF_\d+)\x00/g;
  const allParts = withMarkers.split(COMBINED_MARKER_RE);
  const segments: Segment[] = [];

  let pendingRefs: VideoRefData[] = [];
  let trendCardCount = 0;

  const flushPendingRefs = () => {
    if (pendingRefs.length) {
      segments.push({ kind: "video_refs", refs: [...pendingRefs] });
      pendingRefs = [];
    }
  };

  for (let i = 0; i < allParts.length; i++) {
    const part = allParts[i];

    // Odd indices are marker keys (TREND_CARD_N or VIDEO_REF_N)
    if (i % 2 === 1) {
      if (part.startsWith("TREND_CARD_")) {
        flushPendingRefs();
        const idx = parseInt(part.slice("TREND_CARD_".length), 10);
        if (!isNaN(idx) && trendCards[idx]) {
          segments.push({ kind: "trend_card", data: trendCards[idx], cardIndex: trendCardCount++ });
        }
      } else if (part.startsWith("VIDEO_REF_")) {
        const idx = parseInt(part.slice("VIDEO_REF_".length), 10);
        if (!isNaN(idx) && videoRefs[idx]) {
          pendingRefs.push(videoRefs[idx]);
        }
      }
      continue;
    }

    // Even indices are text chunks
    if (part) {
      flushPendingRefs();
      const lines = part.split("\n");
      let textAccum = "";

      for (const line of lines) {
        const hookMatch = HOOK_LINE_RE.exec(line);
        if (hookMatch) {
          if (textAccum) {
            segments.push({ kind: "text", content: textAccum });
            textAccum = "";
          }
          segments.push({ kind: "hook", text: hookMatch[1] });
        } else {
          textAccum += (textAccum ? "\n" : "") + line;
        }
      }

      if (textAccum) {
        segments.push({ kind: "text", content: textAccum });
      }
    }
  }

  flushPendingRefs();
  return segments;
}

// ---------------------------------------------------------------------------
// Inline markdown renderer (no external deps)
// ---------------------------------------------------------------------------

function renderInline(text: string): React.ReactNode {
  // Split on **bold** markers
  const parts = text.split(/(\*\*[^*]+\*\*)/);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return <strong key={i}>{p.slice(2, -2)}</strong>;
    }
    return p;
  });
}

function MarkdownLine({ line }: { line: string }) {
  const trimmed = line.trimStart();

  // Heading ## or ###
  if (trimmed.startsWith("### ")) {
    return (
      <h3 className="mb-1 mt-3 text-sm font-bold text-[var(--ink)]">
        {renderInline(trimmed.slice(4))}
      </h3>
    );
  }
  if (trimmed.startsWith("## ")) {
    return (
      <h2 className="mb-1.5 mt-4 text-sm font-extrabold text-[var(--ink)]">
        {renderInline(trimmed.slice(3))}
      </h2>
    );
  }

  // Bullet — "- " or "* "
  if (/^[-*] /.test(trimmed)) {
    return (
      <li className="ml-3 list-disc text-sm leading-relaxed text-[var(--ink)]">
        {renderInline(trimmed.slice(2))}
      </li>
    );
  }

  // Horizontal rule
  if (/^---+$/.test(trimmed)) {
    return <hr className="my-3 border-[var(--border)]" />;
  }

  // Empty line
  if (!trimmed) {
    return <div className="h-2" />;
  }

  // Regular paragraph
  return (
    <p className="text-sm leading-relaxed text-[var(--ink)]">
      {renderInline(trimmed)}
    </p>
  );
}

function TextBlock({ content }: { content: string }) {
  const lines = content.split("\n");
  const hasBullets = lines.some((l) => /^\s*[-*] /.test(l));

  if (hasBullets) {
    // Wrap bullet lines in <ul>, non-bullets in <p>
    const nodes: React.ReactNode[] = [];
    let bulletGroup: string[] = [];

    const flushBullets = () => {
      if (bulletGroup.length) {
        nodes.push(
          <ul key={nodes.length} className="my-1 space-y-1 pl-1">
            {bulletGroup.map((b, i) => (
              <MarkdownLine key={i} line={b} />
            ))}
          </ul>
        );
        bulletGroup = [];
      }
    };

    for (const line of lines) {
      if (/^\s*[-*] /.test(line)) {
        bulletGroup.push(line);
      } else {
        flushBullets();
        nodes.push(<MarkdownLine key={nodes.length} line={line} />);
      }
    }
    flushBullets();
    return <div className="space-y-0.5">{nodes}</div>;
  }

  return (
    <div className="space-y-0.5">
      {lines.map((line, i) => (
        <MarkdownLine key={i} line={line} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

interface Props {
  text: string;
  /** When true, renders a simple whitespace-pre-wrap paragraph (streaming state). */
  streaming?: boolean;
}

export function MarkdownRenderer({ text, streaming = false }: Props) {
  const segments = useMemo(() => (streaming ? [] : parseSegments(text)), [text, streaming]);

  if (streaming) {
    return <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink)]">{text}</p>;
  }

  if (!segments.length) return null;

  return (
    <div className="space-y-1">
      {segments.map((seg, i) => {
        if (seg.kind === "video_refs") {
          return <VideoRefStrip key={i} refs={seg.refs} />;
        }
        if (seg.kind === "hook") {
          return <CopyableBlock key={i} text={seg.text} />;
        }
        if (seg.kind === "trend_card") {
          return <TrendCard key={i} data={seg.data} index={seg.cardIndex} />;
        }
        return <TextBlock key={i} content={(seg as TextSegment).content} />;
      })}
    </div>
  );
}
