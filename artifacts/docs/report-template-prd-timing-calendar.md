# Template Expansion PRD — `timing` + content calendar

**Owner:** unassigned · **Status:** spec'd, not implemented · **Created:** 2026-04-22

## Purpose

Absorb `content_calendar` into the existing `timing` template instead of adding a new template kind. Two intents share the same temporal axis and similar data sources; splitting them would duplicate the heatmap layer.

| Intent | User question shape | Today | After |
|---|---|---|---|
| `timing` | "Giờ nào post hiệu quả nhất?" | `timing` template | `timing` template (unchanged) |
| `content_calendar` | "Lên lịch post 7 ngày tới cho mình" | force-fit into `pattern` | `timing` template with populated `calendar_slots[]` |

## What changes visually

Reference design: Claude Chat "Report 3: TIMING" final section (7-day content calendar grid).

After the existing heatmap + top-3 windows section, add a new block:

- **Lịch content tuần (calendar_slots[])** — 7 cells, one per day. Each populated cell shows: suggested post time, suggested content type ("Pattern" / "Ideas" / "Timing" / "Repost best-of"), 1-line title, and a subtle chip for content kind.
- Empty cells render as "—" (greyed) so the plan feels intentional — it's OK to not post every day.

The calendar block is always rendered when `calendar_slots[]` is non-empty. For pure `timing` queries the field stays empty and only the heatmap + windows show.

## Data contract

Extend `TimingPayload` (`cloud-run/getviews_pipeline/report_types.py:161`) — no new envelope kind needed:

```python
class CalendarSlot(BaseModel):
    day_idx: int = Field(ge=0, le=6)                 # 0 = Thứ 2, 6 = Chủ nhật
    day: str                                         # pre-formatted Vietnamese: "Thứ 4"
    suggested_time: str = Field(max_length=12)       # "20:00"
    kind: Literal["pattern", "ideas", "timing", "repost"]  # drives the chip colour
    title: str = Field(max_length=100)               # "Hook cảm xúc mới"
    rationale: str = Field(max_length=200)           # "Khung Thứ 4 20:00 giữ #1 4 tuần liền"

class TimingPayload(BaseModel):
    # ... existing fields unchanged ...
    calendar_slots: list[CalendarSlot] = Field(default_factory=list, max_length=7)  # NEW
```

No new `ReportV1.kind` value. No migration. No dispatcher change.

## Backend builder change

Update `build_timing_report` (`cloud-run/getviews_pipeline/report_timing.py:160`):

1. Accept a `mode: Literal["windows", "calendar"] | None = None` parameter. When `None`, infer from the query: any of `{"lịch", "kế hoạch", "tuần tới", "7 ngày", "calendar", "plan"}` in the normalised query → `"calendar"`.
2. When `mode == "calendar"`, after computing the heatmap + top windows, call a new `_build_calendar_slots(niche_id, query, top_windows, window_days)` helper that:
   - Takes the top 3–5 windows from the heatmap.
   - Queries recent high-retention patterns for the niche (reuse `rank_hooks_for_pattern` from pattern builder).
   - Assigns one pattern/ideas suggestion per top-3 day, plus a `repost` slot on the best weekend day.
   - Returns 3–5 `CalendarSlot`s (not always 7 — an empty Thứ 6 is honest).

Gate: skip the calendar slots entirely when fewer than 3 top windows reach `lift_multiplier >= 1.5` — an unreliable heatmap shouldn't produce a week plan.

## Gemini narrative change

Update `fill_timing_narrative` (`cloud-run/getviews_pipeline/report_timing_gemini.py` — already exists from batch-3) to take `calendar_slots` as optional context:

- When `calendar_slots` is non-empty, the `insight` paragraph opens with a sentence referencing the planned week, not just the top window. Example:
  - Windows-only: "Khung Thứ 4 20:00 đang dẫn đầu — gấp 1.8× ngách."
  - Calendar mode: "Tuần tới nên post 3 video ở Thứ 4/5/7 khung 20:00 — ba cửa sổ đang dẫn đầu ngách."
- `related_questions` should branch toward calendar-related follow-ups when in calendar mode ("Nên hoãn ngày nào nếu kênh mình chỉ post 2 video tuần này?").

The existing query-awareness invariant from batch-3 still holds: two different queries → two different `insight` strings.

## Intent routing change

Update `src/routes/_app/intent-router.ts`:

```ts
// INTENT_DESTINATIONS, line 51-71
content_calendar: "answer:timing",  // was "answer:pattern"
```

Update `select_builder_for_turn` in `cloud-run/getviews_pipeline/answer_session.py` — already dispatches on `kind` for non-primary turns (batch-3 work); no change needed because `timing` already maps correctly.

Add a query-intent hint to the builder call: when dispatching for `content_calendar`, pass `mode="calendar"` so the calendar slots always populate for this intent (not just when the keyword heuristic fires).

## Frontend change

Extend `src/components/v2/answer/timing/TimingBody.tsx`:

1. Import a new sub-component `CalendarStrip.tsx` that renders the 7-day grid. Design tokens only — no hardcoded hex. Cell colour per `kind`:
   - `pattern` → `--gv-pos-soft / --gv-pos-deep` background chip
   - `ideas` → `--gv-accent-soft / --gv-accent-deep`
   - `timing` → `--gv-canvas-2 / --gv-ink-2`
   - `repost` → neutral `--gv-ink / --gv-canvas` inverse
2. Render the strip between the "Top 3 windows" section and the action cards, **only when** `calendar_slots.length > 0`.
3. No changes to the heatmap, variance note, or fatigue band.

Empty state: when a `timing` intent session has no calendar slots (pure windows query), the strip is hidden — not replaced with a placeholder. Cleaner.

## Tests

Backend (`cloud-run/tests/test_report_timing.py`, extend or new):
- `test_calendar_slots_empty_for_pure_timing_query` — "giờ nào tốt nhất?" → `calendar_slots == []`.
- `test_calendar_slots_populated_for_calendar_query` — "lên lịch post tuần tới" → 3–5 slots.
- `test_calendar_slots_skip_when_heatmap_weak` — no window reaches 1.5× lift → empty calendar slots regardless of query.
- `test_calendar_slots_respect_query` — two different calendar queries produce two different slot titles / rationales (batch-3 lesson, extended here).

Frontend (`src/components/v2/answer/timing/CalendarStrip.test.tsx`):
- Renders all 4 `kind` colour variants.
- Hidden when slots array is empty.
- Empty day cells render greyed "—", not omitted (keeps the 7-cell grid alignment).

Dispatcher (`cloud-run/tests/test_answer_turn_builder_dispatch.py`, extend):
- `content_calendar` intent on a primary turn now calls `build_timing_report` with `mode="calendar"`, not `build_pattern_report`.

## Migration

**None.** Adding optional fields to an existing Pydantic model with `default_factory` is forward-compatible. Existing persisted `answer_turns.payload` rows with no `calendar_slots` key continue to validate because the default is `[]`.

## Acceptance

- Lands as one PR. Probably ships before lifecycle + diagnostic because it's smaller scope.
- CI green: pytest + vitest + typecheck + token-lint.
- `content_calendar` intent now routes to `timing` via `INTENT_DESTINATIONS` and populates the calendar strip.
- Manual smoke: a "lên lịch post 7 ngày tới cho kênh skincare" session renders the existing heatmap + a 7-cell calendar strip with 3–5 populated cells.

## Out of scope for v1

- Auto-sync to user's external calendar (Google Calendar, Apple Calendar) — future feature.
- Drag-to-rearrange slots in-UI — read-only for now.
- Per-slot forecast ("Dự báo 12–18K view") — v1 shows kind + title + time only. Forecast is a v2 addition once we trust the estimates.
