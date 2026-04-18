# Thumbnail / cover-frame analysis

Status: **proposed** · Targets: after comment-sentiment lands

## Why

Creators pick covers by stop-power. The corpus today classifies `first_frame_type` as an enum (face / product / text / environment) — useful, not enough. A creator who asks "what should my cover be for this topic?" gets "put a face" instead of "extreme close-up with a startled expression and 3-word overlay 'ĐỪNG MUA KEM'."

The stop-power question has its own micro-skill: composition, text placement, facial expression, colour contrast. One focused Gemini call on frame-0 unlocks it.

## Scope

Add a second, smaller Gemini pass targeted at the first frame of every video. Output is a compact `thumbnail_analysis` block attached to `user_video` and to each reference video in the corpus.

### Output shape

```ts
type ThumbnailAnalysis = {
  stop_power_score: number;          // 0.0–10.0 — composite score
  dominant_element: "face" | "product" | "text" | "environment";
  text_on_thumbnail: string | null;  // verbatim, truncated 40 chars
  facial_expression: "neutral" | "surprised" | "confused" | "smiling" | "focused" | null;
  colour_contrast: "high" | "medium" | "low";
  why_it_stops: string;              // 1 Vietnamese sentence, <= 120 chars
};
```

## Data path

Frames at `[0.0, 1.0, 3.0]s` are already extracted to R2 by the existing ingest (`config.py:140`). Use the `t=0.0` frame URL:

```python
# cloud-run/getviews_pipeline/thumbnail_analysis.py

async def analyze_thumbnail(frame_url: str) -> ThumbnailAnalysis | None:
    """Single Gemini image-understanding call. Returns None on any error."""
    prompt = THUMBNAIL_PROMPT
    image_part = types.Part.from_uri(file_uri=frame_url, mime_type="image/jpeg")
    response = await run_sync(
        _generate_content_models,
        [image_part, prompt],
        primary_model=GEMINI_EXTRACTION_MODEL,
        fallbacks=GEMINI_EXTRACTION_FALLBACKS,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=400,
            response_mime_type="application/json",
            response_json_schema=ThumbnailAnalysis.model_json_schema(),
        ),
    )
    # parse + validate + return
```

## Prompt

```
THUMBNAIL_PROMPT = """Analyze this TikTok cover frame for stop-power.
Return ONLY JSON matching the schema — no markdown.

- stop_power_score (0.0–10.0): composite — face presence, facial expression intensity,
  colour contrast, text readability. A bored neutral face on beige = 3. An extreme
  close-up startled expression with yellow-black text = 9.
- dominant_element: ONE of face / product / text / environment.
- text_on_thumbnail: EXACT visible text, verbatim Vietnamese. Max 40 chars. null if none.
- facial_expression: required ONLY when dominant_element=face. Use the 5 listed values.
- colour_contrast: high = vibrant / complementary, medium = mid-tone, low = washed/muted.
- why_it_stops: ONE Vietnamese sentence naming the specific element, not generic praise.
  GOOD: "Mặt lớn + chữ vàng trên đen + biểu cảm ngạc nhiên."
  BAD: "Hình đẹp và thu hút."
"""
```

## Cost & caching

- Per frame: ~200 input tokens (small image) + ~100 output tokens. Flash-Lite sufficient.
- One extraction per video at corpus-ingest time → `video_corpus.thumbnail_analysis_json` column.
- User-submitted videos: analyze on-demand in `analyze_aweme()`, cache in `full_analyses[video_id]`.
- Skip for carousels (slide 1 already analyzed in carousel extraction).

## Schema migration

```sql
ALTER TABLE video_corpus ADD COLUMN thumbnail_analysis JSONB;
```

RLS: same as existing `video_corpus` columns.

## Integration points

**`video_diagnosis`** — new structured output field `thumbnail_analysis`. Rendered in the frontend as a small tile above the diagnosis narrative:

```
┌────────────────────────────────────┐
│ [frame-0 image]  Stop-power 7.5/10 │
│                  Vì sao dừng: Mặt  │
│                  lớn + chữ vàng    │
└────────────────────────────────────┘
```

Ships as the "Thumbnail nên chỉnh thế nào?" follow-up chip — click triggers a recommendation paragraph (new free `follow_up` turn with the thumbnail_analysis payload in context).

**`content_directions` reference videos** — each reference now carries its thumbnail analysis. Prompt update: name the stop-power technique alongside the hook when discussing the reference.

**`CreatorCard.best_video`** — `thumbnail_analysis.why_it_stops` replaces the generic `why_it_worked` when available (more specific).

## Phases

### Phase 1
- `thumbnail_analysis.py` module + unit tests (against canned Gemini response shapes).
- Wire into `analyze_aweme` for user-submitted videos.
- Migration + corpus column.
- Corpus backfill job (Cloud Run scheduled, rate-limited) for existing rows.

### Phase 2
- Frontend tile in ChatScreen.
- "Thumbnail nên chỉnh thế nào?" chip generates recommendations.

### Phase 3
- Compare two thumbnails (user's video vs niche top-1) side-by-side in the diagnosis output.

## Open questions

1. **Extraction consistency** — should we re-use the main VIDEO_EXTRACTION_PROMPT with an added `thumbnail_analysis` section (one call, richer), or keep it as a separate small call (cheaper retries, cleaner failure isolation)? Recommendation: separate call. Video extraction already carries heavy schema; adding another layer makes it brittle.
2. **Stop-power scoring calibration** — ship rough, collect 2 weeks of scores, adjust the 0-10 bands if they cluster in the middle. Consistent with the rate-ballpark pattern from KOL finder.
3. **R2 frame availability** — Phase 1 assumes all corpus videos have frames extracted. For user-submitted videos outside the corpus, we either (a) extract frame-0 ourselves (ffmpeg call in Cloud Run) or (b) skip the thumbnail pass. Recommendation: (a) — ffmpeg already available in the Cloud Run image per existing pipeline code.
