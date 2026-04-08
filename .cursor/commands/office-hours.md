---
name: office-hours
description: Phase 1 validation gate — validates the northstar and EDS produced externally, then stress-tests the product idea. Run after placing Phase 1 artifacts in artifacts/docs/.
---

# /office-hours — Product Diagnostic (Required Gate)

> **Mandatory. Run after placing Phase 1 artifacts in `artifacts/docs/`.** Phase 1 (northstar + EDS) is produced externally — in Claude.ai, Gemini, or any collaborative process where the team can brainstorm and iterate freely. This command validates that the resulting documents have the structural completeness needed for downstream phases, then stress-tests the product idea.

## Step 1 — Locate or produce Phase 1 artifacts

Check for existing Phase 1 artifacts:
- `artifacts/docs/northstar-*.html`
- `artifacts/docs/emotional-design-system.md` or `artifacts/docs/eds-*.html`

**If artifacts exist:** Read them and proceed to Step 2 (validation) + Step 3 (diagnostic).

**If artifacts don't exist:** Stop. Tell the human to produce Phase 1 artifacts externally first. Point them to `.cursor/skills/phase1/SKILL.md` as the reference template — it specifies all 12 required sections, extraction tests, and the EDS format. Phase 1 is intentionally done outside Cursor (in Claude.ai, Gemini, or any collaborative tool) so the team can brainstorm, share with stakeholders, and iterate freely before committing to a build.

## Step 2 — Northstar structural validation

Validate the northstar against mandatory section requirements. Every section must be present and substantive — not placeholder text.

### Required sections checklist:

| # | Section | Validation rule |
|---|---|---|
| 1 | The Problem | Present, written from user's perspective, no solution language |
| 2 | Primary User | Named person with age, occupation, specific friction moment — not a demographic |
| 3 | The Solution | Present, describes core loop as user experiences it |
| 4 | Revenue Model | Specific price point (not a range or "TBD"), payment trigger defined, revenue math present |
| 5 | Core Value Proposition | Follows the formula: "[App] helps [user] [do X] so that [Y], without [Z]" |
| 6 | Competitive Moat | Moat type named explicitly (data/network/switching cost/distribution/brand) |
| 7 | Build Scope | Table covers core loop, retention, monetization, AND landing page |
| 7b | Landing Page Content | Headline, keywords, trust signals, CTA copy, FAQ items, social proof all present |
| 8 | Not Building | Specific feature names with reasons — no vague categories |
| 9 | Auth Model | Exact method specified, account trigger, profile data, session behavior |
| 10 | External Integrations | Env var names for every service |
| 11 | Payment Integration | Provider named, webhook events listed, test mode documented |
| 12 | Feature Grouping | Maps to build waves with dependencies |
| 13 | User Scenarios | _(B2C only, recommended)_ Credit balance tracked, features tagged |

**For each missing or incomplete section:** Report the specific gap. Use AskUserQuestion format to help the human fill it in.

**If 3+ sections are missing or placeholder:** Stop and tell the human to complete Phase 1 first, using `.cursor/skills/phase1/SKILL.md` as the template.

## Step 3 — The 5-question diagnostic

Work through each question. Compare answers against what the northstar says. Flag misalignments.

### Q1: Who is the specific user?

Not "people who want X" — a specific person. Name, age range, job, daily frustration. The more specific, the better the product.

"Describe one real person who would use this app tomorrow if it existed. What's their day like? Where does this app fit?"

**Validate against northstar §2:** Does the northstar's named archetype match this person? Is the emotional state specific enough?

### Q2: What's the job to be done?

Not a feature list. The job the user is hiring this app to do. Format: "When [situation], I want to [motivation], so I can [expected outcome]."

**Validate against northstar §3:** Does the solution section describe this job clearly?

### Q3: What does the 10-star version look like?

Brian Chesky's framework:
- 5-star: the user completes the core task without friction
- 7-star: the user is delighted by something unexpected
- 10-star: the user tells everyone they know about it

What would make someone text their friend about this app?

**Validate against northstar §6:** Does the moat section describe something that could produce a 10-star moment, or is it generic?

### Q4: What are you intentionally NOT building?

Every app has an anti-scope. Name 3–5 features that sound reasonable but you are choosing to skip. For each: why skip it? What would change your mind?

**Validate against northstar §8:** Are the exclusions specific enough that agents can pattern-match against them?

### Q5: What's the unfair advantage?

Why will this app win where others haven't? Possible answers: unique data, unique distribution, unique insight into the user, existing audience, cost structure, speed of iteration. "No advantage yet" is honest — the advantage must be speed.

**Validate against northstar §6:** Is the moat type the same as the unfair advantage? If not, why?

## Step 4 — Stack fit check

Read `.cursor/skills/architecture/SKILL.md` Section 2 (RAD Stack Constraints). Scan the northstar for requirements that trigger known stack limits:

| Northstar requirement | Check against |
|---|---|
| File uploads mentioned (§7, §10) | Edge Function 2MB body limit. If >5MB files: needs direct-to-Storage upload. |
| Real-time features (§3, §7) | Supabase Realtime 500 connections/channel. If collaborative editing: may exceed RAD stack. |
| Heavy computation (§10, §13) | Edge Function 60s timeout. If >60s processing: needs background task or external service. |
| Complex auth/sharing (§9) | RLS `user_id = auth.uid()` doesn't cover shared resources. If teams/groups: needs membership pattern. |
| Search across large datasets (§7) | Postgres full-text only. If >1M documents or fuzzy matching: evaluate external search. |

**If a constraint is triggered:** Flag it in the synthesis (Step 6). Present options per the architecture skill's "When the stack doesn't fit" guidance. The human decides whether to reduce scope, add a service, accept risk, or abandon RAD.

**If no constraints triggered:** Note "Stack fit: PASS" in the synthesis and proceed.

## Step 4b — Deployment mode validation (if §7c exists)

If the northstar includes §7c (Deployment Mode), validate:

| Check | Validation |
|---|---|
| Mode matches device APIs | If mode is `pwa` but §7c lists Bluetooth/NFC/AR/HealthKit → flag mismatch. |
| Store accounts | If mode ≠ `pwa`: Apple Developer + Google Play enrolled? If not, flag lead times (Apple: 1-3 weeks org, Google: 14-day testing). |
| Google 14-day clock | If mode is `native` or `pwa-then-native`: has 14-day closed testing started? If not, recommend starting immediately with a minimal Expo shell. |
| Phase B trigger | If mode is `pwa-then-native`: is the trigger defined (immediately / after PMF / after Google testing)? |

**If §7c is missing and the app requires native features:** Flag this — recommend adding §7c before proceeding to `/init`.

## Step 5 — Assumptions and risks

Extract the key assumptions the northstar makes about user behavior. For each:

| Assumption | What if it's wrong? | How to validate post-launch |
|---|---|---|
| [e.g., "Users will pay after seeing partial results"] | [What breaks] | [Metric to watch] |

This table becomes `agent-workspace/temp/office-hours-risks.md`. It feeds the dogfooding step later.

## Step 6 — Synthesis

Write a summary combining validation findings, diagnostic answers, and stack fit:

```markdown
## Office Hours Summary

**User:** [specific person description]
**Job to be done:** When [situation], I want to [motivation], so I can [outcome]
**10-star moment:** [the magical thing]
**Not building:** [3–5 explicit exclusions with reasoning]
**Unfair advantage:** [honest assessment]

### Northstar Validation
- Sections present: [X/13]
- Gaps found: [list any missing or weak sections]
- Structural completeness: PASS / NEEDS WORK

### Stack Fit
- [PASS — no constraints triggered / WARNINGS — list each constraint hit with options]

### Assumptions & Risks
[top 3 assumptions, what breaks if wrong, how to validate]

### Recommendation
[1–2 sentences: proceed / fix gaps first / rethink, with reasoning]
```

Save to `agent-workspace/temp/office-hours-summary.md` (gitignored).

## Step 7 — Gate decision

**If all sections pass validation and diagnostic is clear:**
```
Office hours complete. Northstar validated — all 12+ sections present and substantive.
Ready to build. Run /init to scaffold the project.
```

**If northstar has gaps:**
Report each gap with the specific section number and what's missing. Help the human fill them in before proceeding. Do not allow `/init` to proceed with an incomplete northstar.
