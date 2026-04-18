# Output discipline — progressive disclosure for the three richest intents

Status: **approved** · Applies to: `video_diagnosis`, `competitor_profile`, `shot_list`

## Why

Today each of these intents returns one long synthesis. Readers scan, miss the actionable bits, and don't come back for the deeper layers. The JTBD-per-intent evaluation (see "User-perspective audit" session log) surfaced 5-7 concrete "next actions" per response we were burying inside the narrative.

Shipping all of them in a single wall of text is worse than shipping a tight core + pulling the rest via chips. Each chip click is a free `follow_up` turn — same cost as sitting there reading — and the engagement loop is better.

## The rule

For each of the three intents:

1. **Core response** = 3-4 highest-signal items. The things the user cannot leave without.
2. **Deferred items** = everything else the old prompt produced. Each becomes a specific follow-up chip the user clicks when they want it.
3. The synthesis prompt tells the model *explicitly* not to elaborate the deferred items — they have their own chip.

No new data fetches. No new structured components. Pure prompt + follow-up surface reorganisation. Ships without infra changes.

## Per intent

### `video_diagnosis` (Soi Video)

Core response (keep):
- **Verdict line** — one sentence: "Phân phối yếu" vs "Nội dung yếu" vs "Hook yếu" vs "Tốt — thử lại".
- **2-3 root causes** tied to evidence from the user's video.
- **One hook rewrite** — concrete, not a category.
- **Repost/re-edit decision** — one line.

Deferred to chips:
- 3 alternative hooks (detailed) → `"Cho mình 3 hook thay thế chi tiết"`
- Thumbnail direction → `"Thumbnail nên chỉnh thế nào?"`
- Niche benchmark percentiles → `"So sánh với top 10% niche"`
- Next-post action kit (3 changes, A/B test, expected uplift) → `"Gợi ý 3 thay đổi cụ thể cho video tiếp theo"`

### `competitor_profile` (Soi Kênh Đối Thủ)

Core response (keep):
- **Channel verdict** — 1 sentence: why they're winning / their dominant bet.
- **Content mix** one-liner: "70% review · 20% GRWM · 10% trend."
- **Top-1 copyable formula** — the one hook pattern the user should swipe.
- **Differentiation gap** — one line: what they DON'T cover, which the user can own.

Deferred to chips:
- Full top-3 hook library with templates → `"3 công thức hook hay nhất của họ"`
- Posting pattern (cadence + best time) → `"Họ đăng vào khung giờ nào, tuần mấy post?"`
- Monetization signals → `"Họ đang kiếm tiền thế nào?"`
- Brief in their style for the user's niche → `"Tạo brief nhái phong cách của họ cho ngách tôi"`

### `shot_list` (Lên Kịch Bản Quay)

Core response (keep):
- **4-6 scenes** — beats only, no fluff.
- **Hook + ending** spelled out.
- **Runtime estimate**.

Deferred to chips:
- Caption + 5-hashtag bundle → `"Viết caption + 5 hashtag cho video này"`
- Thumbnail/cover directions → `"Gợi ý cover/thumbnail"`
- Filming prep checklist → `"Checklist chuẩn bị quay (dụng cụ, ánh sáng)"`
- Length variants → `"Cho mình bản 15s / 30s / 60s"`

## Prompt-side implementation

Each intent's synthesis prompt already has a rule block. We add one rule:

> **Rxx: KHÔNG nói về [list of deferred items]. Những phần này đã có nút follow-up riêng — người dùng sẽ hỏi khi cần.**

This is cheaper than restructuring the narrative format — we keep all the existing rules about voice, examples, citation, persona — and just list what to skip. The prompt stays the same shape; the output gets tighter.

## Chips

`pipelines._build_follow_ups` gets a richer branch per intent:

- `video_diagnosis` → 3 chips pointing at the deferred items above (rotate if user has context suggesting one is more relevant).
- `competitor_profile` → same pattern.
- `shot_list` → same pattern.

Chips re-enter the chat via `handleSend` → classify as `follow_up` (free) or the specific paid intent when the chip asks for a new turn (e.g. `"Tạo brief nhái phong cách của họ"` classifies as `brief_generation`).

## Out of scope

- New structured fields (content_mix pie chart, trajectory timeline, thumbnail score). Save for a Phase 2 that wires real data pulls.
- Frontend changes. Chips already render from `structured_output.follow_ups`.
- Any new data fetches. All deferred answers are things the current synthesis already knows how to produce — we just defer the elaboration.

## Done criteria

- Each of the three intents' next response is ≤60% the length of the current output.
- Each intent emits 3 tailored chips pointing at the deferred depth.
- Clicking a chip returns the elaborated content the user expected.
- No regression in existing unit/integration tests.
