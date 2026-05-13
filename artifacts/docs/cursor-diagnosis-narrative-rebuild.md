# GetViews Video Diagnosis — Narrative Rebuild
## Complete Cursor Implementation Instructions

**Scope:** Restructure the video diagnosis output to combine structured data with a coherent narrative layer. The current output reads like a technical report — data fragments without a connecting voice. The goal is an advisor tone: opinionated prose first, structured evidence below.

**Test video for validation throughout:**
`https://www.tiktok.com/@curnon.official/video/7638856358812634375`

---

## STEP 0 — DO FIRST: Update TypeScript types and Pydantic models

All new backend fields must be typed before any component or pipeline work begins, or the build will fail.

### FILE: `src/lib/api-types.ts`

Add these interfaces, then extend the existing `VideoDiagnosis` response type to include them:

```typescript
export interface NarrativeVi {
  ket_luan_nhanh: string;
  van_de_chinh: string;
  loi_chinh_narrative: Array<{ error_id: string; narrative: string }>;
  dinh_huong_chien_luoc: string;
}

export interface BrightSpotSignal {
  signal_type: 'hook_only_problem' | 'performing_well' | 'hook_and_distribution' | 'content_and_hook';
  message_vi: string;
}

export interface FormatCard {
  format_name_vi: string;
  mechanism_vi: string;
  view_range: string;
  engagement_rate: string;
  example_hook_vi: string;
}

export interface ChannelContext {
  available: boolean;
  reason?: string;
  top_videos?: Array<{
    aweme_id: string;
    desc: string;
    statistics_play_count: number;
    content_format: string;
    created_at: string;
  }>;
  bottom_videos?: Array<{
    aweme_id: string;
    desc: string;
    statistics_play_count: number;
    content_format: string;
    created_at: string;
  }>;
  format_performance?: Record<string, number>;
  best_performing_format?: string;
  sample_size?: number;
}

// In the existing VideoDiagnosis response type, add:
// narrative_vi: NarrativeVi
// bright_spot_signal: BrightSpotSignal | null
// format_cards: FormatCard[]
// channel_context: ChannelContext
//
// Do NOT add speculative view projections (`view_scenarios` / predicted views if the user changes hook).
```

### Cloud Run: Pydantic response model

Find the Pydantic model in `cloud-run/getviews_pipeline/` that defines the diagnosis SSE response shape (likely `DiagnosisResponse` or similar). Add the fields above to match the TypeScript interfaces. Use `Optional` with `None` defaults so existing sessions without these fields don't break.

---

## STEP 1 — SSE streaming protocol for new fields

The pipeline streams tokens via SSE. The new structured fields are not token streams — they are complete objects. Specify emission timing:

- **`narrative_vi.ket_luan_nhanh`** — emit as a dedicated SSE event of type `ket_luan_nhanh` FIRST, before the main token stream begins. This is 2–3 sentences; the user should see the verdict immediately.
- **`channel_context`** — emit as a dedicated SSE event of type `channel_context` as soon as the channel query completes (run this query in parallel with the main analysis pipeline, not sequentially).
- **`format_cards`, `bright_spot_signal`** — emit on the `narrative_ready` SSE event (along with `narrative_vi` and structured `errors`) when synthesis finishes; do not stream these token-by-token.
- **`narrative_vi` object (including `van_de_chinh` and `loi_chinh_narrative`)** — ship complete on `narrative_ready` (or equivalent closing payload). Do NOT stream these fields token-by-token — partial prose renders badly.

---

## STEP 2 — Add `narrative_vi` to Gemini synthesis prompt

**FILE:** `cloud-run/getviews_pipeline/pipelines.py`
**FUNCTION:** `run_video_diagnosis()` — the final Gemini synthesis call

Add `narrative_vi` as a top-level field in the Gemini output schema:

```json
{
  "narrative_vi": {
    "ket_luan_nhanh": "2-3 câu. Format bắt buộc: [điểm sáng từ metrics] → [vấn đề gốc cụ thể] → [fix duy nhất cần làm ngay]. Dùng số thực. Ví dụ: 'Retention 81% top 5% — nội dung sau hook của bạn tốt. Vấn đề duy nhất là giây đầu tiên: hook tiếng Anh không tạo tò mò với tệp thời trang VN. Đổi một câu mở đầu, phần còn lại giữ nguyên.'",
    "van_de_chinh": "1 đoạn văn 3-4 câu. Giải thích vấn đề lớn nhất bằng ngôn ngữ tự nhiên, có dẫn chứng từ metrics và channel context nếu có. Không dùng danh sách.",
    "loi_chinh_narrative": [
      {
        "error_id": "maps to errors[] array — same error_id string",
        "narrative": "2-3 câu giải thích lỗi này có nghĩa gì với creator cụ thể này. Dùng dữ liệu thực từ video (timestamps, view counts, retention). Không viết lý thuyết chung."
      }
    ],
    "dinh_huong_chien_luoc": "1 đoạn 3-4 câu. Format đang thắng trong ngách này và tại sao nó phù hợp với account này cụ thể. Không chung chung."
  }
}
```

### Tone rules — encode ALL of these into the synthesis prompt directly

```
TONE RULES FOR ALL narrative_vi STRINGS:
- Viết như advisor thẳng thắn, không như báo cáo
- Dùng "video này", "kênh của bạn", "tệp của bạn"
- KHÔNG bắt đầu câu bằng: "Bạn nên", "Hãy thử", "Tuyệt vời", "Tuy nhiên", "Bên cạnh đó"
- KHÔNG dùng các từ sau: bí mật, công thức vàng, triệu view, bùng nổ, viral ngay, đột phá
- KHÔNG bắt đầu response bằng: "Chào bạn", "Wow", "Thật tuyệt"
- Dùng số thực khi có: "231 view trong khi format TB đạt 2,400" không phải "view thấp"
- Dùng tỷ lệ cụ thể: "100x gap" không phải "kém hơn nhiều"
- Nếu có điểm sáng, nêu trước điểm yếu
- Tham khảo đầy đủ copy rules tại .cursor/rules/copy-rules.mdc
```

### If `channel_context.available == true`

In `narrative_vi.van_de_chinh`, instruct Gemini to:
1. Reference the creator's own best-performing video by view count
2. State the gap explicitly: e.g. "22,900 view (format macro close-up) vs 231 view (video này) = 100x gap trên cùng một kênh"
3. Anchor recommendations to what already works on this specific account

If `channel_context.available == false`, omit the account comparison. Do not fabricate.

---

## STEP 3 — `bright_spot_signal`: retention × views diagnostic implication

**FILE:** `cloud-run/getviews_pipeline/pipelines.py`
**LOCATION:** After corpus benchmark computation in `run_video_diagnosis()`

```python
def compute_bright_spot_signal(
    retention_percentile_rank: float | None,  # 0-100 scale, 100 = best
    views_vs_avg_ratio: float | None,         # current_views / format_avg
) -> dict | None:
    """
    Maps the retention×views combination to a named diagnostic pattern.
    
    retention_percentile_rank: use the variable that produces "top 5%"
    in the current output — NOT the raw retention rate (81%).
    These are different: raw rate is 0-100%, rank is a percentile.
    
    views_vs_avg_ratio: current_views / format_avg.
    If format_avg is 0 or None (thin corpus), this function returns None
    for the hook_only_problem case — do not divide by zero.
    """
    if retention_percentile_rank is None:
        return None

    # Cannot compute ratio if corpus is thin
    if views_vs_avg_ratio is None:
        if retention_percentile_rank >= 80:
            return {
                "signal_type": "hook_only_problem",
                "message_vi": f"Retention top {100 - retention_percentile_rank:.0f}% — nội dung sau hook tốt. Corpus ngách còn mỏng nên chưa có view TB để so sánh, nhưng retention cao chỉ ra vấn đề cô lập tại hook."
            }
        return None

    if retention_percentile_rank >= 80 and views_vs_avg_ratio < 0.5:
        return {
            "signal_type": "hook_only_problem",
            "message_vi": f"Retention top {100 - retention_percentile_rank:.0f}% — nội dung sau hook tốt. Vấn đề cô lập tại hook: không cần rewrite toàn bộ video."
        }
    elif retention_percentile_rank >= 80 and views_vs_avg_ratio >= 0.5:
        return {
            "signal_type": "performing_well",
            "message_vi": "Cả hook lẫn nội dung đang hoạt động tốt so với format."
        }
    elif 50 <= retention_percentile_rank < 80 and views_vs_avg_ratio < 0.5:
        return {
            "signal_type": "hook_and_distribution",
            "message_vi": "Hook chưa đủ mạnh và nhịp độ nội dung cần cải thiện."
        }
    else:
        return {
            "signal_type": "content_and_hook",
            "message_vi": "Cả hook lẫn cấu trúc nội dung cần được xem lại."
        }
```

Call this function after the benchmark computation and include `bright_spot_signal` in the response. Pass `None` for `views_vs_avg_ratio` if `format_avg` is 0 or not available.

---

## STEP 4 — Language/market mismatch error detection

**FILE:** `cloud-run/getviews_pipeline/analysis_core.py`
**LOCATION:** After hook text is extracted from transcript/OCR, before structural error assembly

Add `langdetect` to `cloud-run/requirements.txt`: `langdetect>=1.0.9`

```python
import re
from langdetect import detect, LangDetectException

def detect_language_market_mismatch(hook_text: str, target_market: str = "vi") -> dict | None:
    """
    Detects when the hook language does not match the target market.
    target_market defaults to "vi" — in the future derive this from
    the user's profile niche country setting. TODO: make dynamic.
    
    Uses langdetect rather than character heuristics to handle brand
    names (Curnon, Nike, etc.) and mixed bilingual captions correctly.
    """
    if not hook_text or len(hook_text.strip().split()) < 4:
        # Too short to detect reliably — skip
        return None

    # Strip hashtags and mentions before language detection
    clean_text = re.sub(r'#\w+', '', hook_text)
    clean_text = re.sub(r'@\w+', '', clean_text).strip()

    if len(clean_text.split()) < 4:
        return None

    try:
        detected_lang = detect(clean_text)
    except LangDetectException:
        return None

    if detected_lang != target_market:
        return {
            "error_id": "lang_market_mismatch",
            "timestamp_start": 0.0,
            "timestamp_end": 3.0,
            "severity": "CAO",
            "title_vi": "Hook tiếng Anh — thị trường không khớp",
            "description_vi": f'"{hook_text}" là tiếng Anh trên một tài khoản nhắm tệp Việt. Người dùng VN không dừng lại cho câu này.',
            "fix_vi": "Viết lại hook bằng tiếng Việt với góc nhìn cụ thể về nhu cầu tệp. Thay generic call-out bằng POV hoặc câu hỏi gây tò mò."
        }
    return None
```

Inject this error at the **top** of the `errors[]` list (before other structural errors) when it fires — it is always CAO severity and is the most proximate discoverable cause.

---

## STEP 5 — Human presence / personality detection

**FILE:** `cloud-run/getviews_pipeline/analysis_core.py`
**LOCATION:** Gemini vision frame analysis prompt schema

Add two boolean fields to the frame analysis schema that Gemini already processes:

```
"has_human_speaking_to_camera": boolean
  true if any frame shows a person facing camera and appears to be
  speaking or addressing the viewer directly

"has_expressed_opinion_or_question": boolean
  true if the video contains text overlay or audio that states a
  personal opinion ("mình thích", "tại sao", "bạn có biết", "thật ra",
  "mình chọn", "theo mình") or poses a direct question to the viewer
```

Then in structural error assembly:

```python
# Silent formats where no human presence is intentional and correct
SILENT_FORMAT_EXCEPTIONS = {
    'product_display_silent',
    'ambient_lifestyle',
    'macro_closeup_product',
    'aesthetic_broll',
    'text_overlay_only',
}

if (
    not analysis.has_human_speaking_to_camera
    and not analysis.has_expressed_opinion_or_question
    and video.content_format not in SILENT_FORMAT_EXCEPTIONS
):
    errors.append({
        "error_id": "no_human_presence",
        "timestamp_start": 0.0,
        "timestamp_end": video_duration,
        "severity": "TB",
        "title_vi": "Thiếu hiện diện con người — video thuần visual",
        "description_vi": (
            "Video không có giọng nói, không có ý kiến, không có câu hỏi. "
            "Format product showcase thuần visual trong ngách này thường đạt "
            "30–40% view so với format có người kể chuyện."
        ),
        "fix_vi": (
            "Thêm voiceover hoặc text overlay thể hiện quan điểm thật: "
            "'Tại sao mình chọn cái này thay vì X' hoặc 'Lý do duy nhất mình recommend'. "
            "Không cần quay lại — overlay text đủ."
        )
    })
```

---

## STEP 6 — Channel context query (OQ-2)

**FILE:** `cloud-run/getviews_pipeline/routers/video.py`
**LOCATION:** Add as a parallel async step, run concurrently with the main video analysis

### Before writing the query — check column structure

Run this against the database to confirm whether `author_unique_id` is a flat column or inside a JSONB field:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'video_corpus'
AND column_name LIKE 'author%';
```

- If flat column `author_unique_id` → use `.eq("author_unique_id", author_unique_id)`
- If JSONB column `author` with nested `unique_id` → use `.eq("author->>unique_id", author_unique_id)`

Do not assume — check first.

### Implementation

```python
async def fetch_channel_context(
    author_unique_id: str,
    current_video_id: str,
    supabase_service_client,  # use the existing service_role client — do NOT create a new one
) -> dict:
    """
    Queries video_corpus for this creator's recent videos to build a hit/flop pattern.
    Run this in parallel with the main analysis pipeline, not sequentially.
    """
    try:
        result = await supabase_service_client.table("video_corpus") \
            .select("aweme_id, desc, statistics_play_count, content_format, created_at") \
            .eq("author_unique_id", author_unique_id) \
            .neq("aweme_id", current_video_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        # NOTE: adjust filter key above based on column check result

        if not result.data or len(result.data) < 2:
            return {"available": False, "reason": "Chưa đủ lịch sử kênh để so sánh"}

        videos = result.data
        sorted_by_views = sorted(
            videos, key=lambda v: v.get("statistics_play_count", 0), reverse=True
        )

        format_groups: dict[str, list[int]] = {}
        for v in videos:
            fmt = v.get("content_format", "unknown")
            format_groups.setdefault(fmt, []).append(v.get("statistics_play_count", 0))

        format_avgs = {
            fmt: sum(views) / len(views)
            for fmt, views in format_groups.items()
        }
        best_format = max(format_avgs, key=format_avgs.get) if format_avgs else None

        return {
            "available": True,
            "top_videos": sorted_by_views[:2],
            "bottom_videos": sorted_by_views[-2:],
            "format_performance": format_avgs,
            "best_performing_format": best_format,
            "sample_size": len(videos),
        }

    except Exception:
        # Non-fatal — diagnosis continues without channel context
        return {"available": False, "reason": "Lỗi truy vấn lịch sử kênh"}
```

Pass the `channel_context` result to the Gemini synthesis prompt AND emit it as an SSE event (see Step 1).

---

## STEP 7 — View / hook-change projections (DO NOT IMPLEMENT)

**Product rule:** GetViews must not show **predicted view counts** or “what happens if you change hook” ladders. That reads like guaranteed outcomes and is prohibited.

- Do **not** add `view_scenarios`, `compute_view_scenarios`, or any UI table labeled “Kịch bản dự đoán” / projected views after fixes.
- Actionable direction stays in **`narrative_vi`** (including `dinh_huong_chien_luoc`), **error FIX blocks**, **format_cards**, and existing **script / rewrite CTAs** elsewhere in the answer body — without numeric view forecasts.

---

## STEP 8 — Format cards (narrative layer over existing corpus data)

**FILE:** `cloud-run/getviews_pipeline/pipelines.py`
**LOCATION:** Cross-niche signal synthesis section

**Important:** Format cards are a NEW section, not a replacement for the existing cross-niche signal table. The architecture is:

1. Existing corpus aggregation runs as-is → produces the hook-type table data (keep this)
2. That same aggregated data is ALSO passed to Gemini → Gemini adds `format_name_vi`, `mechanism_vi`, and `example_hook_vi`
3. Frontend renders BOTH: format cards (new, prominent) AND the existing hook table (kept, moved to bottom as supporting detail)

Gemini must not hallucinate format card data. The `view_range` and `engagement_rate` fields must be derived from corpus numbers, not invented.

Instruct Gemini to output `format_cards` as part of the synthesis response:

```json
"format_cards": [
  {
    "format_name_vi": "Tên format ngắn gọn, dễ nhớ. Ví dụ: 'Đồng hồ trong outfit OOTD'",
    "mechanism_vi": "1-2 câu: TẠI SAO format này hoạt động về mặt tâm lý người xem",
    "view_range": "Lấy từ corpus data — ví dụ: '50K–200K'. Không bịa.",
    "engagement_rate": "Lấy từ corpus data — ví dụ: '5–8%'. Không bịa.",
    "example_hook_vi": "1 câu hook mẫu theo format này, tiếng Việt, dưới 15 từ, ready to use"
  }
]
```

Limit to 3 format cards.

`example_hook_vi` must comply with copy rules:
- Tiếng Việt
- Không bắt đầu bằng "Bạn có biết" hoặc "Khám phá"
- Không dùng các từ cấm trong `.cursor/rules/copy-rules.mdc`
- Dưới 15 từ
- Nghe như creator thật nói, không phải slogan marketing

---

## STEP 9 — Frontend layout restructure

**FILES:** `src/routes/_app/answer/AnswerScreen.tsx` and components in `src/components/v2/answer/`

Preserve all existing data queries and hooks. Only restructure rendering order and component hierarchy.

### New section order (top to bottom)

```
1. KẾT LUẬN NHANH          ← NEW  (narrative_vi.ket_luan_nhanh)
2. HIỆU SUẤT VIDEO          ← EXISTING refactored (add bright_spot_signal row)
3. VẤN ĐỀ CHÍNH             ← NEW  (narrative_vi.van_de_chinh)
4. LỖI CẤU TRÚC             ← EXISTING refactored (add narrative lead per error)
5. NGỮ CẢNH KÊNH            ← NEW  (channel_context — only if available)
6. ĐỊNH HƯỚNG CHIẾN LƯỢC   ← NEW  (format_cards) + prose (`dinh_huong_chien_luoc`) where wired in VideoBody
7. TÍN HIỆU LIÊN NGÁCH      ← EXISTING, moved to bottom (keep as-is)
```

---

### Section 1: KẾT LUẬN NHANH

```tsx
// Full-width banner, rendered before metric grid
// Shown as soon as ket_luan_nhanh SSE event arrives — do not wait for diagnosis_complete
<div className="w-full rounded-lg bg-primary/10 p-4 mb-4">
  <p className="text-foreground leading-relaxed max-w-[680px]">
    {narrative_vi.ket_luan_nhanh}
  </p>
</div>
```

---

### Section 2: HIỆU SUẤT VIDEO (refactor existing metric grid)

Add a `bright_spot_signal` row below the existing metric grid. Only render if `bright_spot_signal` is not null.

```tsx
{bright_spot_signal && (
  <div className="mt-2 rounded bg-muted px-3 py-2">
    <p className="text-sm text-foreground leading-relaxed">
      ⚡ {bright_spot_signal.message_vi}
    </p>
  </div>
)}
```

---

### Section 3: VẤN ĐỀ CHÍNH

```tsx
// Rendered as prose — NOT as a list or structured card
<section className="mb-6">
  <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-2">
    Vấn đề chính
  </h3>
  <p className="text-foreground leading-relaxed max-w-[680px]">
    {narrative_vi.van_de_chinh}
  </p>
</section>
```

---

### Section 4: LỖI CẤU TRÚC (refactor error cards)

Each error card gets a narrative lead sentence above the existing structured detail. The structured detail (timestamp, description, fix) becomes collapsible. The collapsible is open by default for the first CAO error, closed for TB and THẤP.

```tsx
// Before implementing <Collapsible>:
// Check if src/components/ui/collapsible.tsx exists.
// If yes, import from there.
// If no, implement with useState toggle — do NOT install any new package.
// A chevron icon + conditional render is sufficient.

<ErrorCard key={error.error_id}>
  {/* Severity badge — keep existing */}
  <SeverityBadge severity={error.severity} />

  {/* Title — keep existing */}
  <h4>{error.title_vi}</h4>

  {/* NEW: narrative lead — rendered as prose, always visible */}
  {narrativeLead && (
    <p className="text-foreground leading-relaxed mt-1 mb-2 max-w-[640px]">
      {narrativeLead}  {/* from narrative_vi.loi_chinh_narrative[i].narrative */}
    </p>
  )}

  {/* Collapsible: structured detail */}
  <Collapsible defaultOpen={error.severity === 'CAO' && isFirst}>
    <CollapsibleTrigger>Chi tiết & cách sửa ▾</CollapsibleTrigger>
    <CollapsibleContent>
      <Timestamp start={error.timestamp_start} end={error.timestamp_end} />
      <p>{error.description_vi}</p>
      <FixBlock fix={error.fix_vi} />
      <ApplyToScriptCTA />  {/* keep existing CTA — do not remove */}
    </CollapsibleContent>
  </Collapsible>
</ErrorCard>
```

---

### Section 5: NGỮ CẢNH KÊNH (new section)

Only render if `channel_context.available === true`.

Show the creator's top 2 hit videos alongside the current video in a comparison layout:

```tsx
{channel_context?.available && (
  <section className="mb-6">
    <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
      Ngữ cảnh kênh · @{author_unique_id}
    </h3>
    <div className="grid grid-cols-1 min-[700px]:grid-cols-3 gap-3">
      {channel_context.top_videos?.map(v => (
        <VideoComparisonCard
          key={v.aweme_id}
          desc={v.desc}
          views={v.statistics_play_count}
          format={v.content_format}
          badge="HIT"
        />
      ))}
      <VideoComparisonCard
        desc={currentVideo.desc}
        views={currentVideo.views}
        format={currentVideo.content_format}
        badge="VIDEO NÀY"
        highlight
      />
    </div>
    {/* Gap callout — only if ratio is extreme */}
    {gapRatio >= 10 && (
      <p className="mt-2 text-sm text-muted-foreground">
        Gap: {gapRatio}x giữa format tốt nhất và video này trên cùng kênh.
      </p>
    )}
  </section>
)}
```

---

### Section 6: ĐỊNH HƯỚNG CHIẾN LƯỢC (format cards — new section)

```tsx
<section className="mb-6">
  <h3 className="...">Định hướng chiến lược</h3>
  <div className="grid grid-cols-1 min-[700px]:grid-cols-3 gap-3">
    {format_cards.map(card => (
      <div key={card.format_name_vi} className="rounded-lg border border-default p-4">
        <p className="font-semibold text-foreground mb-1">{card.format_name_vi}</p>
        <p className="text-sm text-muted-foreground leading-relaxed mb-2">
          {card.mechanism_vi}
        </p>
        <p className="text-xs text-muted-foreground mb-1">
          {card.view_range} · {card.engagement_rate}
        </p>
        <div className="mt-2 rounded bg-muted px-2 py-1">
          <p className="text-xs text-foreground italic">"{card.example_hook_vi}"</p>
        </div>
      </div>
    ))}
  </div>
</section>
```

---

### Section 7: TÍN HIỆU LIÊN NGÁCH

Keep the existing cross-niche hook table exactly as-is. Move it to the bottom of the layout. No other changes.

---

### Prose rendering rules (apply globally to all narrative fields)

```
- Render as <p> tags, never as <div> or <li>
- Font: default body font (NOT JetBrains Mono — that is for numbers only)
- leading-relaxed (Tailwind, line-height 1.625)
- max-w-[680px] on desktop to prevent overly wide prose lines
- text-foreground (not text-muted-foreground — these are primary findings)
- Do not apply additional formatting (bold, italic) inside narrative prose
  unless the narrative string itself contains markdown markers
```

---

## STEP 10 — Tests

### `cloud-run/tests/test_language_detection.py`

```python
from getviews_pipeline.analysis_core import detect_language_market_mismatch

def test_vietnamese_hook_returns_none():
    assert detect_language_market_mismatch("Tại sao mình chọn đồng hồ này") is None

def test_english_hook_returns_error():
    result = detect_language_market_mismatch("Hey look at this watch")
    assert result is not None
    assert result["error_id"] == "lang_market_mismatch"
    assert result["severity"] == "CAO"

def test_brand_name_only_returns_none():
    # "Curnon" alone should not trigger — too short
    assert detect_language_market_mismatch("Curnon") is None

def test_hashtag_stripped_before_detection():
    # Hook is Vietnamese; hashtags are English — should not trigger
    assert detect_language_market_mismatch("Phối đồ hôm nay #fashion #OOTD") is None

def test_very_short_hook_returns_none():
    assert detect_language_market_mismatch("Yes") is None
    assert detect_language_market_mismatch("OK go") is None
```

### `cloud-run/tests/test_bright_spot.py`

```python
from getviews_pipeline.pipelines import compute_bright_spot_signal

def test_hook_only_problem():
    result = compute_bright_spot_signal(
        retention_percentile_rank=95.0,  # top 5%
        views_vs_avg_ratio=0.1,          # far below average
    )
    assert result["signal_type"] == "hook_only_problem"

def test_performing_well():
    result = compute_bright_spot_signal(
        retention_percentile_rank=85.0,
        views_vs_avg_ratio=0.7,
    )
    assert result["signal_type"] == "performing_well"

def test_thin_corpus_with_high_retention():
    result = compute_bright_spot_signal(
        retention_percentile_rank=90.0,
        views_vs_avg_ratio=None,  # corpus too thin
    )
    assert result is not None
    assert result["signal_type"] == "hook_only_problem"

def test_zero_format_avg_returns_none_not_error():
    # Should not raise ZeroDivisionError
    result = compute_bright_spot_signal(
        retention_percentile_rank=50.0,
        views_vs_avg_ratio=None,
    )
    assert result is None  # not enough signal

def test_low_retention_any_views():
    result = compute_bright_spot_signal(
        retention_percentile_rank=30.0,
        views_vs_avg_ratio=0.3,
    )
    assert result["signal_type"] == "content_and_hook"
```

## DO NOT CHANGE

The following must remain untouched:

- Auth flow, Supabase RLS, credit deduction (`TD-1` — `decrement_credit()` RPC)
- PayOS webhook handling (`TD-2` — `processed_webhook_events` idempotency)
- `profiles.is_processing` guard (`TD-3`)
- SSE reconnect buffer: `stream_id + seq` emission (`TD-4`) — only ADD new event types, do not modify existing ones
- Carousel pipeline — Option A frontend guard in `intent-router.ts` stays as-is
- Any route outside `/app/answer`
- `video_corpus` INSERT path — still batch-only via service_role
- `src/components/ui/` component library — extend what exists, do not add shadcn/ui or HeroUI
- Vietnamese copy rules in `.cursor/rules/copy-rules.mdc` — all new strings must comply

---

## VALIDATION CHECKLIST

After all steps, submit this video and verify each item:

**URL:** `https://www.tiktok.com/@curnon.official/video/7638856358812634375`

```
[ ] narrative_vi.ket_luan_nhanh appears at top before analysis completes
[ ] ket_luan_nhanh mentions retention AND hook language — not generic
[ ] bright_spot_signal fires as "hook_only_problem" (retention is top 5%)
[ ] lang_market_mismatch error fires — hook is "Hey look at this"
[ ] lang_market_mismatch appears FIRST in errors list
[ ] no_human_presence error fires (no talking head in video)
[ ] If channel_context returned data: creator's own ~23K videos shown
[ ] If channel_context unavailable: section hidden, no fabrication
[ ] No UI or API field projects views after hook/format changes (no `view_scenarios`)
[ ] format_cards has exactly 3 entries with Vietnamese hooks under 15 words
[ ] narrative prose renders as <p>, not lists, max-w-[680px] on desktop
[ ] First CAO error collapsible is open by default; TB/THẤP are closed
[ ] Existing TÍN HIỆU LIÊN NGÁCH section still present at bottom
[ ] TypeScript build passes with no new errors
[ ] Cloud Run + frontend tests for narrative / bright spot / video body pass
```
