# Class intelligence UI spec — Morning Signal (Wave 3a)

**Status:** PD approved · 2026-05-22  
**Surface:** Studio Home Tier I — signal strip above `StudioHero`  
**Related:** [`two-axis-niche-model.md`](two-axis-niche-model.md) §10, plan §9

---

## Max-2-Card rule

| Slot | Allowed `lifecycle_stage` | Max count |
|------|---------------------------|-----------|
| Opportunity | `new_class`, `emerging`, `growing` | 1 |
| Defensive | `declining` | 0–1 |
| **Total** | — | **≤ 2** |

- Default: show 1 opportunity only — do not pad defensive card.
- Defensive shown only when `video_count_7d ≥ 5` AND user junction has ≥1 declining class.
- Dismiss same `content_class_id` → hide 48h (`localStorage` key `gv_signal_dismiss_{id}`).

---

## Signal object schema (composed at FE — not stored on MV)

```typescript
interface ClassMorningSignal {
  content_class_id: number;
  label_vn: string;
  signal_type: "new_class" | "emerging" | "growing" | "declining" | "peak";
  avg_views: number | null;
  delta_pct: number | null; // null when new_class or prior_7d = 0
  suggested_hook_type: string | null;
  suggested_sound: string | null;
  window_hours: 36;
  corpus_citation: string; // e.g. "47 video · 7 ngày"
}
```

**`delta_pct`:** `(view_velocity - 1) * 100` for emerging/growing; **hidden** for `new_class`.

---

## Copy (Vietnamese)

| signal_type | Headline | Body pattern |
|-------------|----------|--------------|
| `new_class` | Mới xuất hiện trong ngách | `{label_vn} — {sample_size} video 7 ngày qua, chưa có baseline tuần trước.` |
| `emerging` | Format đang tăng tốc | `{label_vn} — view TB ↑{delta_pct}% so với tuần trước ({corpus_citation}).` |
| `growing` | Đang lên | Same as emerging, softer tone |
| `declining` | Format đang chững | `{label_vn} — lượng video mới giảm {abs(delta)}% tuần này.` |

CTA primary: **Tạo kịch bản** → `/app/answer?q=…` via `scriptPrefillFromMorningSignal`.

Secondary: **Xem phân tích chuyên sâu** → `/app/trends`.

---

## Gates (fail-open)

- No signal when `claim_tier = 'thin'` or `video_count_7d < 5`.
- No signal when junction empty or user has no `creator_niche_id`.
- `useTopPatterns` Tier II unchanged — parallel, not replaced.

---

## Sort order

1. `new_class` → `emerging` → `growing` (opportunity pool)
2. Within tier: `COALESCE(view_velocity, format_momentum, 0) DESC`
3. Apply Max-2-Card after sort
