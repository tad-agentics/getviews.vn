import { EvidenceVideoEmbed } from "@/components/v2/answer/video/EvidenceVideoEmbed";
import type {
  FormatCard,
  FormatCardExample,
  ReferenceVideoCard,
} from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

function atHandle(raw: string | null | undefined): string {
  const s = (raw ?? "").trim();
  if (!s) return "";
  return s.startsWith("@") ? s : `@${s}`;
}

function pickFormatCorpusEvidence(card: FormatCard): FormatCardExample | null {
  const xs = card.format_examples;
  if (!xs?.length) return null;
  const id = card.evidence_aweme_id;
  if (id) {
    const hit = xs.find((e) => e.aweme_id === id);
    if (hit) return hit;
  }
  return xs[0];
}

export function FormatCardsGrid({
  cards,
  referenceVideos,
}: {
  cards: FormatCard[];
  referenceVideos: ReferenceVideoCard[];
}) {
  if (!cards.length) return null;

  return (
    <section className="mb-6">
      <h3 className="gv-mono mb-3 text-[11px] font-semibold gv-kicker tracking-[0.18em] text-[color:var(--gv-ink-4)]">
        Format đang hoạt động trong ngách này
      </h3>
      <div
        className={
          cards.length === 1
            ? "grid grid-cols-1 gap-3"
            : "grid grid-cols-1 gap-3 md:grid-cols-2 min-[1440px]:grid-cols-3"
        }
      >
        {cards.map((card, i) => {
          const corpusEv = pickFormatCorpusEvidence(card);
          const refHit = card.evidence_aweme_id
            ? referenceVideos.find((r) => r.aweme_id === card.evidence_aweme_id)
            : undefined;
          const featuredId = refHit?.aweme_id ?? corpusEv?.aweme_id ?? null;
          const moreExamples = (card.format_examples ?? []).filter((ex) =>
            featuredId ? ex.aweme_id !== featuredId : true,
          );
          const hasEvidence = Boolean(refHit ?? corpusEv);

          return (
            <div
              key={`${card.format_name_vi}-${i}`}
              className="flex flex-col rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4"
            >
              <h4 className="mb-1 text-sm font-semibold text-foreground">
                {card.format_name_vi}
              </h4>
              <p className="mb-2 text-[12px] leading-snug text-[color:var(--gv-ink-2)]">
                {card.mechanism_vi}
              </p>
              <div className="mb-2 flex flex-wrap gap-3 text-[11px]">
                <span className="gv-mono text-[color:var(--gv-ink-3)]">{card.view_range}</span>
                <span className="gv-mono text-[color:var(--gv-ink-3)]">{card.engagement_rate}</span>
              </div>
              {card.example_hook_vi ? (
                <p className="mb-2 text-[11px] italic text-[color:var(--gv-ink-3)]">
                  &ldquo;{card.example_hook_vi}&rdquo;
                </p>
              ) : null}
              {hasEvidence ? (
                <>
                  <p className="gv-mono mb-2 text-[11px] font-semibold gv-kicker tracking-[0.14em] text-[color:var(--gv-ink-3)]">
                    Minh chứng trong kho
                  </p>
                  <EvidenceVideoEmbed
                    aweme_id={card.evidence_aweme_id ?? null}
                    reference_videos={referenceVideos}
                    corpusExample={corpusEv}
                  />
                </>
              ) : (
                <p className="mb-2 text-[11px] leading-snug text-[color:var(--gv-ink-3)]">
                  Chưa có video minh chứng từ kho cho format này.
                </p>
              )}
              {moreExamples.length >= 1 ? (
                <div className="mb-2 border-t border-[color:var(--gv-rule)] pt-3">
                  <p className="gv-mono mb-2 text-[11px] font-semibold gv-kicker tracking-[0.14em] text-[color:var(--gv-ink-3)]">
                    Ví dụ thực tế
                  </p>
                  <div className="space-y-1.5">
                    {moreExamples.map((ex) => (
                      <a
                        key={ex.aweme_id}
                        href={ex.tiktok_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between gap-2 text-[11px] text-[color:var(--gv-ink-2)] transition-colors hover:text-[color:var(--gv-accent)]"
                      >
                        <span className="min-w-0 truncate">
                          {atHandle(ex.creator_handle)} · {ex.desc || "(không có caption)"}
                        </span>
                        <span className="gv-mono shrink-0 font-semibold tabular-nums text-[color:var(--gv-ink)]">
                          {formatViews(ex.play_count)}
                        </span>
                      </a>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
