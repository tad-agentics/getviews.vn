# Comment sentiment + purchase-intent radar

Status: **proposed** · Targets: PR after viral-pattern-fingerprint lands

## Why

Sellers picking KOLs and creators benchmarking videos both ask the same unvoiced question: *"do viewers actually care, or are they just passing through?"* Views answer the passive question; comments answer the active one. One video with 5K views + 200 "tôi sẽ mua" comments converts better than another with 500K views + emoji spam.

Today GetViews doesn't read comments. Every downstream output — KOL cards, creator profiles, diagnosis — underweights the single strongest conversion proxy.

## Scope — Phase 1

Attach a compact `comment_radar` field to per-video payloads and, by aggregation, to each `CreatorCard`. No new frontend component — the badge renders into existing cards.

### Data shape

```ts
type CommentRadar = {
  sampled: number;               // comments actually read (cap 50)
  total_available: number;       // from EnsembleData statistics.comment_count
  sentiment: {
    positive_pct: number;        // "like this!", "cute", "helpful"
    negative_pct: number;        // "scam", "don't believe", "won't work"
    neutral_pct: number;         // everything else (default bucket)
  };
  purchase_intent: {
    count: number;               // hits from purchase-intent regex
    top_phrases: string[];       // up to 3 verbatim examples, truncated 80 chars
  };
  questions_asked: number;       // how many comments contain "?" or "giá", "link", "ở đâu"
  language: "vi" | "mixed" | "non-vi";  // dominant comment language
};
```

## Data source

**EnsembleData** endpoints to investigate:

- `/post/comments?aweme_id=` — primary candidate. Needs Cloud Run-side rate-limit handling (each call = 1 EnsembleData unit).
- `fetch_post_info` already returns `statistics.comment_count` — we already have the denominator for free.

If `/post/comments` isn't available on our plan, fallback: scrape top comments from the aweme response (usually includes 3-5 pinned comments). Partial signal, same code path.

## Phase-1 helper module

`cloud-run/getviews_pipeline/comment_radar.py` — pure functions except for the one `fetch_comments(video_id)` ensemble wrapper:

```python
PURCHASE_INTENT_PATTERNS = [
    r"\btôi\s+sẽ\s+(mua|thử|order|đặt)",
    r"\b(cần|muốn)\s+(mua|thử|order)",
    r"\b(giá|price)\s+(bao\s*nhiêu|sao|ntn)",
    r"\blink\s*(đâu|bio|shopee|tiktok\s*shop)",
    r"\b(đặt|order)\s+ở\s+đâu",
    r"\bshopee|\btiktok\s*shop",
    r"\bdm|\binbox\s+(mình|e|em)",
]

POSITIVE_PATTERNS = [
    r"\b(đỉnh|tuyệt\s*vời|xuất\s*sắc|xịn\s*xò|chất\s*lượng)",
    r"\bhay\s+quá", r"\bthích\s+quá", r"\bmê",
    r"❤|😍|🔥|💯|👏",
]

NEGATIVE_PATTERNS = [
    r"\b(lừa\s*đảo|scam|fake|giả)",
    r"\b(không\s+tin|chả\s+tin|hoang\s*đường)",
    r"\b(dở|chán|tệ|nhảm)",
    r"\b(phí\s+tiền|phí\s+thời\s+gian)",
    r"👎|🤮|😒",
]

def score_comments(comments: list[str]) -> CommentRadar: ...
```

Unit-tested against a canned corpus of ~40 Vietnamese TikTok comments spanning the six clusters (buy intent, question, positive, negative, spam, off-topic).

## Caching

`video_comment_radar` table or reuse `video_corpus.comment_radar_json` column (simpler):

```sql
ALTER TABLE video_corpus ADD COLUMN comment_radar JSONB;
ALTER TABLE video_corpus ADD COLUMN comment_radar_fetched_at TIMESTAMPTZ;
```

TTL: 7 days. Older → refetch on next use.

## Integration

- **`CreatorCard.commerce`** gains aggregated purchase-intent count across the creator's last-20 posts. Cheap — we already fetch those posts. Each one has `aweme_id`; we do a DB round-trip for cached radar. Videos without cached radar skipped (no live fetch in Phase 1).
- **`video_diagnosis` structured_output** gains a `comment_radar` key — renders as a small badge row under the diagnosis text.
- **`creator_search` chips** — new chip: *"Xem comments của @handle có 'tôi sẽ mua' không?"* forces a comment fetch on demand.

## Cost guardrails

- Cap at 50 comments per video (EnsembleData pages).
- Cache for 7 days.
- Only fetch on explicit paid-intent paths (creator_search, competitor_profile, video_diagnosis) — never on free intents.
- Budget alarm: Cloud Run log warning if comment_radar_fetched_at column grows faster than N/day.

## Phases

- **Phase 1**: helper module + regex + unit tests + on-demand fetch in video_diagnosis.
- **Phase 2**: nightly backfill for videos in video_corpus (rate-limited).
- **Phase 3**: aggregate into CreatorCard, frontend badge.

## Open questions

1. Do we support English comments for international creators? Phase 1 says Vietnamese-first; English tier is a Phase 2 want.
2. Spam detection — do we filter bot/emoji-only comments before sampling? Recommendation: yes, at ingest time; keeps signal-to-noise high.
3. Do we store verbatim `top_phrases` given privacy? Commenters are public; truncating to 80 chars and stripping @handles is acceptable.
