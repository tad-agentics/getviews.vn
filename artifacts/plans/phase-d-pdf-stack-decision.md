# Phase D.0.iv — PDF rendering stack decision

**Date:** 2026-04-20
**Blocks:** D.1.1 (`draft_scripts` + script save + Copy / PDF / Chế độ quay)
**Status:** Decision locked — **Option A (WeasyPrint)**

---

## Verification of baseline

No PDF rendering dep exists today:

```
$ grep -n "weasyprint\|reportlab\|Pango\|Cairo" cloud-run/pyproject.toml cloud-run/Dockerfile
(no matches)
```

Clean slate — the decision here drives the first PDF ship.

---

## Options

| # | Option | Pros | Cons | Image bloat | Vietnamese support |
|---|---|---|---|---|---|
| A | **WeasyPrint** (HTML→PDF via Pango/Cairo) | Best typography fidelity; direct HTML/CSS → PDF; no font registration dance | ~50 MB system packages (`libpango-1.0-0`, `libcairo2`, `libpangoft2-1.0-0`, `libharfbuzz0b`); slower cold start | **~50 MB** | ✅ Pango handles diacritics natively |
| B | **ReportLab** (pure-Python, programmatic drawing) | Tiny footprint; no system deps; battle-tested | Manual layout; Vietnamese diacritics require explicit TTF registration (`TTFont("Inter", "…")`) per font; no HTML input | **~5 MB** | ⚠️ Needs explicit font registration per weight; easy to miss combining marks |
| C | **Server-side React (Puppeteer / Playwright)** | Reuse existing React components verbatim | Node sidecar container; 10× the deploy complexity; slowest render | ~150 MB Chromium | ✅ Browser renders like the web |

---

## Decision: **Option A — WeasyPrint**

### Rationale

1. **Typography fidelity.** Draft-scripts are Vietnamese-first
   documents with mono blocks, serif title, mixed weight — CSS
   authoring is the right primitive. ReportLab's programmatic drawing
   makes the "shot list table" layout (mono timestamps, bold tag,
   serif voice line, italic note) awkward to maintain and easy to
   drift from the `/app/script` web rendering.
2. **Vietnamese diacritics.** Combining marks (`ổ`, `ỷ`, `ẵ`,
   `ặ`…) are common. Pango handles these natively; ReportLab needs
   every TTF registered with explicit combining-glyph support. One
   missed font weight = rendering bug.
3. **Reuse of existing tokens.** WeasyPrint consumes CSS; we already
   have `--gv-*` design tokens as CSS custom properties. The PDF
   export can link `src/app.css` directly and reuse the
   `--gv-ink`/`--gv-paper`/`--gv-rule` palette without a second source
   of truth.
4. **50 MB budget is acceptable.** Current Cloud Run image runs at
   ~600 MB (Python 3.11 + pydantic + supabase + google-genai +
   boto3 + pyroaring + numpy+pandas transitively). 50 MB is < 10%
   growth — well within the budget `phase-c-plan.md` §D.1.1 allotted.

### Fallback contract (unchanged from C.8.1)

If the D.1.1.0 half-day spike validation fails (Cloud Build can't
install Pango/Cairo system packages; rendering produces corrupt PDF
for Vietnamese input; cold-start latency > 3s), fall back to
**Copy-only**:

- `POST /script/drafts/:id/export` rejects `format=pdf` with HTTP 501
  and `{"error": "pdf_unavailable"}`.
- Frontend `ScriptSaveControls` disables the PDF button with
  `title="Sắp có"`.
- Copy path remains functional.
- File an issue documenting the failure mode + raise the
  ReportLab/server-side-React decision for Phase E or a
  stop-the-bleed hotfix.

---

## Implementation contract for D.1.1

### `cloud-run/pyproject.toml` — dep add

```toml
[project]
dependencies = [
  # ... existing ...
  "weasyprint>=63.0",
  "jinja2>=3.1.0",  # HTML template rendering for the export view
]
```

### `cloud-run/Dockerfile` — system package install

```dockerfile
# Pango/Cairo for WeasyPrint (Phase D.1.1 PDF export).
# Pinned with apt-get install -y --no-install-recommends to minimise bloat.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libharfbuzz0b \
      libcairo2 \
      libffi-dev \
    && rm -rf /var/lib/apt/lists/*
```

### Sample render (D.1.1.0 spike exit criterion)

The D.1.1.0 spike must produce a sample `draft_script.pdf` with:

- Vietnamese title containing `ẵ` / `ỷ` / `ặ` combining marks.
- 6-row shot-list table with mono timestamps + serif voice lines.
- Accent-coloured CTA block at the bottom (`--gv-accent`).
- File size < 200 KB (Vietnamese font embedding check).

PDF committed to `artifacts/qa-reports/phase-d-d0-pdf-sample.pdf`
when the spike passes. The commit that adds the dep must also link
that artifact from `phase-d-design-audit-script-save.md` closure
check.

---

## Cold-start measurement (D.1.1.0 spike deliverable)

Before/after Cloud Run cold-start latency must not exceed the Phase B
baseline (currently ~1.6s cold start for the `getviews-pipeline`
service). WeasyPrint is imported lazily only inside the export
handler; `gunicorn` workers don't pay the Pango init cost unless
`/script/drafts/:id/export?format=pdf` fires.

If cold-start regresses past 2.5s, fall back to Option B (ReportLab)
per the contract above.

---

## Sign-off

WeasyPrint chosen as the Phase D PDF stack. Dep lines for
`pyproject.toml` + `Dockerfile` drafted above. Sample-render contract
locked for D.1.1.0 spike. Copy-only fallback ladder preserved from
C.8.1.

**Deliverable merged; unblocks D.1.1.**
