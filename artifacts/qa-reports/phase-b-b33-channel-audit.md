# Phase B · B.3.3 audit — `/app/channel` + `FormulaBar`

**Date:** 2026-04-19  
**Scope:** Shipped B.3.3 (`ChannelScreen`, `FormulaBar`, `useChannelAnalyze`) vs `artifacts/plans/phase-b-plan.md` §B.3.3 + `artifacts/uiux-reference/screens/channel.jsx`.  
**Token check (B.3.5-style):** `src/routes/_app/channel/*.tsx`, `src/components/v2/FormulaBar.tsx` — no raw `#hex` in JSX; colors use `var(--gv-*)` or server-driven `bg_color` on thumbnails only.

---

## Must-fix (shipped in same PR as this audit)

| Item | Spec | Finding | Resolution |
|------|------|-----------|------------|
| Thin-corpus empty copy | Plan §B.3.2 table + L737–740: mono 11px, **ink-4**, centered; copy **“Chưa đủ video để dựng công thức”** | `FormulaBar` used shorter copy and **ink-3** | Aligned copy + `text-[color:var(--gv-ink-4)]` |
| Posting cadence chip | Fixture mapping L760: client joins `posting_cadence` + `posting_time` with **` · `** | Only `posting_cadence` shown | `ChannelScreen` builds one chip from both fields |

---

## Should-fix

| Item | Finding | Note |
|------|---------|------|
| Plan nav typo L803 | Doc says `/channel?handle=`; app correctly uses **`/app/channel`** | Treat as doc drift; no app change |
| `tiktok-page` modal in `QuickActionModal` | Still builds a chat prompt for profile URL | B.3.4 routes **Soi Kênh** quick path to `/app/channel`; legacy `tiktok-page` key unused in `EmptyStates` — optional cleanup later |
| `ChannelScreen` dynamic `backgroundColor` | `v.bg_color` from API may be hex | Acceptable for API-sourced swatches; not a design-token regression |

---

## Consider

| Item | Note |
|------|------|
| **B.3.5** full design audit | Still run `artifacts/qa-reports/phase-b-design-audit-channel.md` with section-by-section `must-fix / should-fix / consider` before closing B.3 |
| `PostingHeatmap` | Deferred per plan — chip cadence is acceptable |
| Formula section title | Reference uses “4 bước”; live data may be &lt;4 steps — current “các bước” wording is fine |

---

## Verdict

**B.3.3 functional requirements:** met (route, JWT GET wiring, `FormulaBar`, thin gate, `KpiGrid`, top videos → `/app/video`, lessons).  
**Gaps closed above:** thin empty typography/copy; posting chip join string.  
**B.3.4 (same rollout):** chat no longer streams `competitor_profile` / `own_channel` for new sends — navigates to `/app/channel` (handle from message, profile `tiktok_handle`, or empty). Empty-state **Soi Kênh** modal + home **QuickActions** “Soi kênh đối thủ” → `/app/channel`. KOL **Phân tích kênh đầy đủ** → `/app/channel?handle=…`. Helpers in `src/lib/channelHandle.ts` + Vitest coverage.

**Re-verify (B.3.5 pass):** Must-fix rows in this file were confirmed still satisfied in `FormulaBar.tsx` + `ChannelScreen.tsx` before closing B.3.5; full design audit + any extra parity fixes live in [`phase-b-design-audit-channel.md`](phase-b-design-audit-channel.md).
