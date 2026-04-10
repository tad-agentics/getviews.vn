/**
 * MarkdownRenderer — renders synthesis markdown with enriched blocks.
 *
 * Parses the plain text synthesis output from Gemini and upgrades specific
 * patterns into visual components:
 *
 *   1. video_ref JSON blocks  → VideoRefStrip (P0-2)
 *      {"type":"video_ref","video_id":"...","handle":"@x","views":1100000,"days_ago":6}
 *
 *   2. Hook: lines            → CopyableBlock (P0-3)
 *      "Hook: ĐỪNG [hành động] nếu chưa xem video này"
 *      "**Hook:** [Sản phẩm] chỉ [giá] — mua ở đâu?"
 *
 *   3. Markdown formatting     → bold (**text**), headings (##), bullets (-)
 *      (lightweight inline — no full markdown parser dependency)
 *
 * Buffering: video_ref blocks are detected as complete JSON objects only,
 * never partially — so incomplete streaming tokens are rendered as plain text
 * until the closing brace arrives and the block is detected on the next render.
 */
import { useMemo } from "react";
import { VideoRefStrip, type VideoRefData } from "./VideoRefStrip";
import { CopyableBlock } from "./CopyableBlock";

// ---------------------------------------------------------------------------
// Segment types
// ---------------------------------------------------------------------------

type TextSegment = { kind: "text"; content: string };
type VideoRefSegment = { kind: "video_refs"; refs: VideoRefData[] };
type HookSegment = { kind: "hook"; text: string };

type Segment = TextSegment | VideoRefSegment | HookSegment;

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

const HOOK_LINE_RE = /^\*{0,2}Hook:\*{0,2}\s+(.+)$/;
const VIDEO_REF_RE = /\{"type"\s*:\s*"video_ref"[^}]*\}/g;

function parseSegments(text: string): Segment[] {
  if (!text.trim()) return [];

  // Step 1: extract all video_ref JSON objects and replace with markers
  const videoRefs: VideoRefData[] = [];
  const indexed: string[] = [];

  const withMarkers = text.replace(VIDEO_REF_RE, (match) => {
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

  // Step 2: split on VIDEO_REF markers, then process each text chunk line by line
  const parts = withMarkers.split(/\x00VIDEO_REF_(\d+)\x00/);
  const segments: Segment[] = [];

  // Consecutive video_refs that appear adjacent get grouped into one strip
  let pendingRefs: VideoRefData[] = [];

  const flushPendingRefs = () => {
    if (pendingRefs.length) {
      segments.push({ kind: "video_refs", refs: [...pendingRefs] });
      pendingRefs = [];
    }
  };

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];

    // Even indices are text chunks; odd indices are ref index strings
    if (i % 2 === 1) {
      const refIdx = parseInt(part, 10);
      if (!isNaN(refIdx) && videoRefs[refIdx]) {
        pendingRefs.push(videoRefs[refIdx]);
      }
      continue;
    }

    // Text chunk — split into lines, detect Hook: lines
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
        return <TextBlock key={i} content={seg.content} />;
      })}
    </div>
  );
}
