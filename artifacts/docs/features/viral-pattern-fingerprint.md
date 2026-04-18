# Viral pattern fingerprint — clustering for cross-video pattern recognition

Status: **proposed** · Targets: the PR after `claude/video-analysis-enrichment` merges

## Why

A creator scrolling TikTok unconsciously notices "this hook is everywhere this week." GetViews doesn't. Today every video in `video_corpus` is an island — we can tell you *this single video* uses a question hook with 1.2 cuts/second, but we can't say *"this video is instance #84 of the 'warning-hook + before/after' pattern, up from 12 instances last week, now spreading from skincare to fitness."*

That last sentence is the actual value proposition vs doomscrolling. Pattern fingerprints unlock it.

## What we're building

### 1. Pattern signature

A pattern is a coarse tuple of features that define the creative formula. Videos sharing a tuple belong to the same pattern.

```
signature = (
    hook_type,                    # one of 14 (already enum)
    content_arc,                  # 6 values (already enum)
    tone,                         # 8 values (already enum)
    energy_level,                 # 3 values
    tps_bucket,                   # bucket(transitions_per_second, [0, 0.5, 1, 1.5, 2, 3])
    face_first_bool,              # face_appears_at < 1.0
    has_text_overlay,             # len(text_overlays) > 0
)
```

Hash → `pattern_id` (deterministic, reproducible).

### 2. New tables

Migration: `supabase/migrations/YYYYMMDD_video_patterns.sql`

```sql
CREATE TABLE video_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signature_hash TEXT NOT NULL UNIQUE,
  signature JSONB NOT NULL,
  display_name TEXT,                 -- human label assigned by nightly job, e.g. "Cảnh báo + Trước/Sau"
  first_seen_at TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL,
  instance_count INTEGER NOT NULL DEFAULT 0,
  niche_spread INTEGER[] NOT NULL DEFAULT '{}',   -- distinct niche_ids seen
  weekly_instance_count INTEGER NOT NULL DEFAULT 0,
  weekly_instance_count_prev INTEGER NOT NULL DEFAULT 0,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX video_patterns_signature_hash_idx ON video_patterns (signature_hash);

ALTER TABLE video_corpus ADD COLUMN pattern_id UUID REFERENCES video_patterns(id);
CREATE INDEX video_corpus_pattern_id_idx ON video_corpus (pattern_id) WHERE pattern_id IS NOT NULL;
```

RLS: authenticated users SELECT only, service_role for nightly writes.

### 3. Nightly job

`cloud-run/getviews_pipeline/pattern_fingerprint.py`:

```python
def compute_signature(analysis: dict) -> tuple: ...
def signature_hash(sig: tuple) -> str: ...

async def upsert_patterns_for_niche(niche_id: int) -> PatternStats:
    # 1. Select video_corpus rows WHERE niche_id=... AND pattern_id IS NULL
    # 2. For each, compute signature + hash
    # 3. Upsert video_patterns row (incrementing instance_count, extending niche_spread)
    # 4. UPDATE video_corpus SET pattern_id = ... WHERE video_id = ...
    # 5. Recompute weekly_instance_count + weekly_instance_count_prev for all
    #    patterns touched this run
```

Scheduled: `supabase/functions/cron-pattern-fingerprint/` — runs at 5 AM ICT daily, one hour after the corpus ingest.

### 4. Integration points (read side)

**`trend_spike` synthesis payload** gains a `patterns` key:
```json
{
  "patterns": [
    {
      "display_name": "Cảnh báo + Trước/Sau",
      "instance_count_week": 34,
      "instance_count_prev_week": 8,
      "weekly_delta": "+325%",
      "niche_spread_count": 5,
      "signature": {"hook_type": "pain_point", "content_arc": "before_after", ...}
    }
  ]
}
```
Prompt update: cite the top-delta pattern in the trend opening.

**`content_directions` reference videos** each carry `pattern_id` + the pattern's display_name. Synthesis prompt instruction: group the directions by pattern family when cohesive, name the family explicitly.

**`video_diagnosis`** gets a new line in the 5-part narrative: "Your video = instance #17 of '{pattern_name}' ({rising|stable|declining}). Pattern has spread to {N} niches this month."

**`CreatorCard.best_video.why_it_worked`** includes the pattern name when available.

### 5. API surface

- `/app/patterns` (future frontend route, Wave 3) — browse patterns table, filter by niche, by delta, by spread.
- Cloud Run `/patterns/list?niche_id=...&window=7d` endpoint for the explore page.

## Phasing

### Phase 1 (this spec when built)
Migration + nightly job + trend_spike integration. ~3-4 days.

### Phase 2
content_directions + video_diagnosis integration. Display name heuristic using the top-performing video's `content_direction.what_works` field.

### Phase 3
Explore page surface — requires frontend work. Patterns browsable standalone.

## Cost

Nightly job cost:
- Supabase: ~1 full-table scan of `video_corpus` nightly (already happens for breakout_multiplier — piggyback).
- No new Gemini calls. Pure rule-based clustering.
- Storage: one UUID column on `video_corpus` + a small patterns table (~hundreds of rows per niche).

## Open questions

1. **Signature granularity** — the 7-tuple above may cluster too aggressively (everything becomes "question + story + educational") or too finely (every video is unique). Recommendation: ship the tuple, log cluster size distribution for 1 week, tune bucket edges.
2. **Display name generation** — static template ("{hook_type_vi} + {arc_vi}") works but reads weak. Better option: one Gemini call per new pattern with the signature + 3 example video analyses, ask for a snappy Vietnamese label. Costs ~100 Gemini calls per niche weekly — acceptable.
3. **Pattern staleness** — a pattern that hasn't had a new instance in 30 days should be pruned or marked dormant. Add `is_active` column and flag in the nightly job.

## Regression guard

Unit test against the pattern clustering logic with canned analysis dicts to ensure:
- Two videos with identical signatures produce identical hashes.
- Different signatures produce different hashes.
- Bucket edges are stable (TPS 1.49 vs 1.51 don't collapse).
- Missing optional fields degrade gracefully (empty text_overlays → has_text_overlay=False).
