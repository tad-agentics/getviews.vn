# /visual-audit [staging-url]

Dispatch the Product Designer for a full visual fidelity audit on the staging deployment.
Runs after all feature waves pass QA, before `/pre-handoff`.

Usage: `/visual-audit https://[app]-staging.vercel.app`

## Pre-flight checks

Before dispatching, confirm:
- [ ] All features in `artifacts/plans/project-plan.md` are marked complete (all QA PASS)
- [ ] Staging URL is live and accessible
- [ ] A staging URL argument was provided

If any check fails: report to human, do not dispatch.

## Dispatch

Launch Product Designer subagent (foreground):

```
Task: Post-Build Visual Fidelity Audit

Read:
- .cursor/agents/product-designer.md (your full instructions — see Post-build section)
- .cursor/rules/design-system.mdc (AI Slop Guard rules)
- .cursor/rules/copy-rules.mdc (copy quality test)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/design-system-spec.md
- artifacts/docs/screen-specs-[app]-v1.md (all screen metadata)
- artifacts/docs/northstar-[app].html (§7b landing page content)

Staging URL: [staging-url]

Compare staging screens against **`artifacts/uiux-reference/screens/`** (or git history / optional `src/make-import/`).
Do NOT use Figma MCP tools — they do not work with Make.

Run the full visual fidelity audit:
- **Make fidelity (CRITICAL)** — since screens are copied directly from Make, every Tailwind class, spacing value, color, font-weight, border-radius, and animation timing must be IDENTICAL to Make's original code. Any visual difference means the agent modified code it shouldn't have. Compare staging against the tracked UIUX reference (or git history). Flag every deviation as BLOCKING.
- AI Slop Guard rules (design-system.mdc)
- Token compliance — no raw colors, no arbitrary spacing
- Mobile viewport at 375px — every screen
- All four interaction states visible — default / loading / error / empty
- No placeholder text or lorem ipsum
- Copy quality — run 5-question Copy Quality Test on all visible copy
- Dopamine moment fidelity — for D1–D4 flagged screens: verify animation timing matches EDS §6. Since Make implemented these, they should be untouched — if timing differs, the agent modified animation code it shouldn't have.
- Share card rendering — if applicable

Landing page specific checks (at `/`):
- All 8 sections present and visible
- View page source — full HTML present (pre-rendered, not empty SPA shell)
- CTA fires install prompt (Android) or shows iOS instructions
- FAQ accordion functional, all items from §7b present
- Already-installed state handled

Signal completion with a findings report.
```

## After completion

**If no BLOCKING findings:**
1. Update project-plan.md — mark visual audit complete
2. Report to human: "Visual audit complete. No blocking findings. Ready for `/pre-handoff`."

**If BLOCKING findings:**
1. Present findings to human
2. Dispatch Frontend Developer to fix each BLOCKING item
3. After fixes: re-run `/visual-audit [staging-url]`
