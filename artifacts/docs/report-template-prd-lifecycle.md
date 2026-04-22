# Template PRD — `lifecycle`

**Owner:** unassigned · **Status:** spec'd, not implemented · **Created:** 2026-04-22

## Purpose

Replace the `pattern` force-fit for 3 intents whose shape is about **decay or segmentation over time**, not ranked hook winners:

| Intent | User question shape |
|---|---|
| `format_lifecycle_optimize` | "Hook/format X còn chạy được nữa không?" |
| `fatigue` | "Hook 'mình vừa test' còn hiệu quả không?" |
| `subniche_breakdown` | "Trong skincare có ngách con nào đang nổi?" |

All three share the same rendering primitive: **a set of entities, each with a lifecycle stage pill + growth chip + bar, optionally grouped.**

## What the page shows

Reference design: Claude Chat "Report 6: FORMAT" (Format Lifecycle + Sub-niche Breakdown). Use as directional, adapt to production constraints below.

Required sections, in order:

1. **Confidence strip** — `ConfidenceStrip` primitive (existing).
2. **Subject line** — 1 sentence naming the subject of the decay analysis (e.g. "Short-form đang lên, long-form đang giảm").
3. **Lifecycle cells** — the primary rail. For `format_lifecycle_optimize` and `fatigue`: a list of entities (format names / hook types) with stage pill, reach delta, retention chip, and bar showing current health score. For `subniche_breakdown`: a grid of sub-niche cards with growth chip + video count + stage pill.
4. **Refresh moves** *(only when stage = declining or plateau)* — 2–3 tactics to refresh the declining entity. Gemini-generated, query-aware.
5. **Action cards** — existing `ActionCardPayload` primitives.
6. **Related questions** — existing shape, query-aware.

## Data contract

New Pydantic model in `cloud-run/getviews_pipeline/report_types.py`. The shape handles all three intents via a `mode` discriminator so we don't ship three near-identical payloads.

```python
class LifecycleCell(BaseModel):
    name: str                                           # "Short-form 15-30s" or "Ingredient deep-dive"
    stage: Literal["rising", "peak", "plateau", "declining"]
    reach_delta_pct: float                              # +28.0 / -12.0
    health_score: int = Field(ge=0, le=100)             # drives the bar width
    retention_pct: float | None = None                  # None for subniche mode
    instance_count: int | None = None                   # video count; None for format mode
    insight: str = Field(max_length=240)                # 1 sentence: why this stage

class RefreshMove(BaseModel):
    title: str = Field(max_length=120)                  # "Đổi sound sang trending VN tuần này"
    detail: str = Field(max_length=280)
    effort: Literal["low", "medium", "high"]

class LifecyclePayload(BaseModel):
    confidence: ConfidenceStrip
    mode: Literal["format", "hook_fatigue", "subniche"]  # discriminator
    subject_line: str = Field(max_length=200)
    cells: list[LifecycleCell] = Field(min_length=1, max_length=12)
    refresh_moves: list[RefreshMove] = Field(default_factory=list, max_length=4)
    actions: list[ActionCardPayload]
    sources: list[SourceRow]
    related_questions: list[str]
```

Add `"lifecycle"` to:
- `ReportV1.kind` Literal union
- `validate_and_store_report` dispatch
- `answer_sessions.format` CHECK constraint (migration)
- `AnswerSessionFormat` in `src/routes/_app/intent-router.ts`
- `select_builder_for_turn` return set in `answer_session.py`
- `INTENT_DESTINATIONS` mapping for the 3 intents

## Backend builder

New module `cloud-run/getviews_pipeline/report_lifecycle.py`:

```python
def build_lifecycle_report(
    niche_id: int,
    query: str,
    mode: Literal["format", "hook_fatigue", "subniche"],
    window_days: int = 30,
) -> dict[str, Any]:
    """Live lifecycle report. Falls back to thin-corpus fixture when niche has <N samples."""
```

Data sources by mode:
- **`format`** — aggregate `video_corpus` grouped by `content_format` with weekly bucketing to compute trend direction. Use the new `pattern_lifecycle_30d` RPC or derive from existing `hook_effectiveness.trend_direction`.
- **`hook_fatigue`** — single hook focus: look up the hook in `video_patterns`, read `weekly_instance_count` streak (needs BUG-11 fix already on main to produce non-zero values). Stage = declining if streak of decreases ≥ 3.
- **`subniche`** — group `video_corpus` rows in the parent niche by cluster hint (hashtag prefix + Gemini clustering, or lean on existing `niche_taxonomy.subclusters` if that table is populated).

Gate thresholds:
- Format mode: skip if fewer than 4 distinct content_formats have ≥10 instances in window.
- Fatigue mode: skip if the hook has fewer than 15 instances in window.
- Subniche mode: skip if fewer than 3 subclusters reach ≥20 instances.

When gated, produce a thin-corpus variant of the payload (same shape, fewer cells, explicit `confidence.intent_confidence = "low"`).

## Gemini narrative

New module `cloud-run/getviews_pipeline/report_lifecycle_gemini.py` following the pattern from batch-3 (`report_timing_gemini.py`, `report_ideas_gemini.py`):

- `fill_lifecycle_narrative(query, mode, niche_label, cells, ...)` → `{subject_line, refresh_moves, related_questions}`.
- Gemini-backed with a query-aware deterministic fallback.
- Prompt must open with a direct answer to `query` using the ranked cells, same structure as the other narrative modules.

Regression test: two different queries on the same niche + mode produce two different `subject_line`s and `related_questions` lists.

## Frontend

New directory `src/components/v2/answer/lifecycle/`:
- `LifecycleBody.tsx` — top-level component dispatched by `ContinuationTurn.tsx`.
- `LifecycleCell.tsx` — the primary rail item (reused across all 3 modes).
- `LifecyclePill.tsx` — stage pill (extract from the reference design; reuse from Pattern if we add the pill there too).
- `RefreshMovesList.tsx` — conditional list, only when declining/plateau cells exist.

Respect the design-system rules:
- No hardcoded hex. Use `var(--gv-*)` tokens.
- JetBrains Mono for all numbers (instance counts, percentages).
- Stage pill colours: `rising → --gv-pos-soft / --gv-pos-deep`, `peak → --gv-accent-2-soft / --gv-accent-deep`, `plateau → --gv-canvas-2 / --gv-ink-3`, `declining → --gv-accent-soft / --gv-accent`.

Add a case to `ContinuationTurn.tsx` switch. Add `"lifecycle"` to `ANSWER_ERROR_CODES` whitelist.

## Tests (must land with the template)

Backend (`cloud-run/tests/test_report_lifecycle.py`):
- `test_payload_validates_in_all_three_modes` — format / hook_fatigue / subniche produce a valid ReportV1.
- `test_thin_corpus_variant_when_gated` — niche with <threshold samples returns the low-confidence variant, not an exception.
- `test_query_drives_narrative` — two different queries → two different `subject_line` strings (pins the lesson from the 2026-04-22 "follow-ups look identical" bug).
- `test_refresh_moves_only_when_declining_or_plateau` — invariant: rising/peak cells never have refresh_moves.

Frontend (`src/components/v2/answer/lifecycle/LifecycleBody.test.tsx`):
- Renders all 3 modes from fixture payloads.
- Stage pill colour matches stage enum.
- `refresh_moves` section hidden when empty.

Dispatcher (`cloud-run/tests/test_answer_turn_builder_dispatch.py`, extend):
- A session with `format = "lifecycle"` on a `primary` turn calls `build_lifecycle_report`, not pattern.

## Migration

```sql
-- 2026-05-XX_add_lifecycle_format.sql
ALTER TABLE answer_sessions
  DROP CONSTRAINT IF EXISTS answer_sessions_format_check;
ALTER TABLE answer_sessions
  ADD CONSTRAINT answer_sessions_format_check
  CHECK (format IN ('pattern', 'ideas', 'timing', 'generic', 'lifecycle', 'diagnostic'));
```

Coordinate with the `diagnostic` migration so they ship together — one CHECK constraint change, not two.

## Acceptance

- Lands as one PR off `claude/report-templates-audit` (or a stacked branch).
- CI green: pytest + vitest + typecheck + token-lint.
- The three intents above route to `lifecycle` instead of `pattern` via `INTENT_DESTINATIONS`.
- Manual smoke test: a `/app/answer` session for each of the 3 intents renders the new template and the narrative text mentions the user's question.

## Out of scope for v1

- Time-series curve visualisation (we show stage pill + bar only; a real curve comes later when we have weekly history in the RPC).
- Comparing two hooks head-to-head in fatigue mode (v2 addition).
- Cross-niche subcluster discovery (v1 only works within a single niche).
