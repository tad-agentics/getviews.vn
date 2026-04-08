# /phase3

> **Phase 3 is absorbed into Figma Make + Foundation.** This command is not dispatched separately.

Figma Make handles visual design (colors, typography, spacing, components). The design system component inventory is produced during `/foundation` when the Frontend Developer catalogs `src/make-import/`.

**If you're looking for the old Phase 3 workflow:**
- Make prompt guidance → `artifacts/docs/figma-make-brief.md` (produced by `/phase2`)
- Component inventory → produced during `/foundation` (see `.cursor/skills/design-system/SKILL.md`)
- Token config → Make's CSS custom properties (`theme.css` with `@theme inline`) copied into `src/app.css` during `/foundation`

**The workflow is now:**
1. `/phase2` → screen specs + Make prompt brief
2. Human builds in Figma Make → copies code to `src/make-import/`
3. `/phase4` → tech spec (schema derived from Make's mock data)
4. `/setup` → build plan
5. `/foundation` → backend infra + component inventory + landing page + auth
