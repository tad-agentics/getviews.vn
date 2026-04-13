# Cursor Implementation Instructions — Corpus Intelligence

Spec for batch job updates that improve the data quality of `video_corpus` and
`niche_intelligence`, enabling stronger evidence-backed claims in diagnosis synthesis.

---

## Phase 3 — Batch Job: Distribution Annotations

**Status:** ✅ Implemented  
**Migration:** `20260411000028_distribution_annotations.sql`  
**Files changed:** `corpus_ingest.py`, `supabase/migrations/`

### What this adds

3 columns on `video_corpus`, computed during batch insert from data already in the
EnsembleData response. Zero additional API calls. Zero incremental cost.

```python
# ============================================================
# DISTRIBUTION ANNOTATIONS — compute during batch insert
# These are NOT quality gates. Do NOT filter on them.
# They annotate each video for corpus intelligence queries.
# ============================================================

GENERIC_HASHTAGS = frozenset({
    'fyp', 'foryou', 'foryoupage', 'viral', 'trending', 'trendingtiktok',
    'tiktok', 'tiktokviral', 'fy', 'xyzbca', 'xyz', 'trend',
    'ootd', 'fashion', 'beauty', 'food', 'funny', 'comedy', 'love',
    'music', 'dance', 'art', 'photography', 'travel', 'fitness',
    'makeup', 'skincare', 'style', 'outfit', 'recipe', 'diy',
    'learnontiktok', 'edutok',
})

def annotate_distribution(hashtags: list[str], caption: str | None) -> dict:
    """
    Compute distribution annotations from ED metadata.
    Returns dict to merge into the corpus row.
    """
    import re

    # 1. Hashtag specificity: at least 1 hashtag NOT in the generic list?
    #    Column: has_vietnamese_hashtags (naming is legacy — actually means "has_specific_hashtags")
    tags_lower = [t.lower() for t in (hashtags or [])]
    has_specific = any(t not in GENERIC_HASHTAGS for t in tags_lower)

    # 2. Caption has real text beyond hashtags?
    has_caption_text = False
    if caption:
        stripped = re.sub(r'#\w+\s*', '', caption).strip()
        has_caption_text = len(stripped) > 10

    # 3. Hashtag count
    hashtag_count = len(tags_lower)

    return {
        'has_vietnamese_hashtags': has_specific,  # True = at least 1 niche-specific hashtag
        'has_caption_text': has_caption_text,      # True = caption has text beyond #hashtags
        'hashtag_count': hashtag_count,
    }
```

### Existing quality gates (unchanged)

The batch job has 5 quality gates in `ingest_niche()` that filter candidates
**before** analysis. Distribution annotations are computed **after** analysis,
inside `_build_corpus_row()`, on the rows that pass all gates:

| Gate | What it filters | Config env var |
|---|---|---|
| Gate 1 | `play_count == 0` — no real stats | — |
| Gate 2 | `play_count < BATCH_MIN_VIEWS` | `BATCH_MIN_VIEWS` (default 20,000) |
| Gate 3 | `author.region` not VN | — |
| Gate 4 | Caption has no Vietnamese diacritics (when region absent) | — |
| Gate 5 | Engagement rate < `BATCH_MIN_ER` | `BATCH_MIN_ER` (default 2.0%) |

Distribution annotations add a **Group E** to `_build_corpus_row()`'s return dict,
alongside existing Groups A–D.

### `niche_intelligence` view update

The materialized view is refreshed to add 4 new distribution norm columns:

```sql
-- Distribution norms per niche
pct_has_specific_hashtags =
  COUNT(*) FILTER (WHERE has_vietnamese_hashtags) * 100.0 /
  NULLIF(COUNT(*) FILTER (WHERE has_vietnamese_hashtags IS NOT NULL), 0),

pct_has_caption_text =
  COUNT(*) FILTER (WHERE has_caption_text) * 100.0 /
  NULLIF(COUNT(*) FILTER (WHERE has_caption_text IS NOT NULL), 0),

avg_hashtag_count = AVG(hashtag_count),

pct_original_sound =
  COUNT(*) FILTER (WHERE is_original_sound = TRUE) * 100.0 /
  NULLIF(COUNT(*) FILTER (WHERE is_original_sound IS NOT NULL), 0),
```

NULLIF guards prevent division-by-zero before any rows are backfilled.

### What this enables in synthesis

The diagnosis prompt already receives `niche_norms` from `get_niche_intelligence()`.
Once the corpus grows, `pct_has_specific_hashtags` and `pct_has_caption_text` become
data-backed claims instead of rules of thumb:

> "92% top video trong ngách skincare có caption mô tả + hashtag cụ thể cho ngách.
> Video bạn chỉ có 4 hashtag tiếng Anh chung chung (#trending #ootd) — thuật toán
> không biết đẩy cho ai."

The corpus grows → the percentages sharpen → the diagnosis becomes more valuable.
Corpus at 380 videos produces stronger claims than at 50. No prompt changes needed;
the data flows through `niche_norms` automatically.

### Schema diff

```sql
-- New columns on video_corpus
has_vietnamese_hashtags  BOOLEAN   -- True = ≥1 niche-specific hashtag
has_caption_text         BOOLEAN   -- True = caption has ≥10 non-hashtag chars
hashtag_count            INTEGER   -- total hashtag count

-- New columns on niche_intelligence (materialized view)
pct_has_specific_hashtags  NUMERIC  -- % of corpus with specific hashtags
pct_has_caption_text       NUMERIC  -- % of corpus with real caption text
avg_hashtag_count          NUMERIC  -- avg hashtag count per video
pct_original_sound         NUMERIC  -- % using original sound
```

### Backfill

Existing rows in `video_corpus` will have `NULL` for the 3 new columns until
re-ingested. `niche_intelligence` uses `NULLIF(COUNT(...) FILTER (...), 0)` so the
percentages return NULL (not 0%) before enough data is present. The synthesis prompt
should treat NULL distribution norms the same as empty `niche_norms` — skip the
distribution comparison section entirely.

No backfill migration is provided. Rows accumulate annotations on the next batch run.
If backfill is needed, use the pattern in `20260411000021_backfill_corpus_from_analysis_json.sql`.

### Indexes

```sql
CREATE INDEX idx_corpus_specific_hashtags
  ON video_corpus(niche_id, has_vietnamese_hashtags)
  WHERE has_vietnamese_hashtags IS NOT NULL;

CREATE INDEX idx_corpus_caption_text
  ON video_corpus(niche_id, has_caption_text)
  WHERE has_caption_text IS NOT NULL;
```

Partial indexes (WHERE IS NOT NULL) exclude pre-migration NULLs from scans.

---

## Previous phases

| Phase | What | Migration | Status |
|---|---|---|---|
| Phase 1 | 30 classification columns (hook_type, content_format, dialect, etc.) | `000020` | ✅ |
| Phase 2 | Backfill existing rows from analysis_json | `000021` | ✅ |
| Phase 3 | Distribution annotations (has_vietnamese_hashtags, has_caption_text, hashtag_count) | `000028` | ✅ |
