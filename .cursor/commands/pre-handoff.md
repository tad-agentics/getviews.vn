# /pre-handoff

Dispatch the QA Agent for the pre-handoff safety audit.
Runs after all feature waves pass QA and the visual fidelity audit is complete.

## Pre-flight checks

Before dispatching, confirm:
- [ ] All features in `artifacts/plans/project-plan.md` are marked complete
- [ ] Visual fidelity audit complete — all BLOCKING items fixed (run `/visual-audit [url]` if not done)
- [ ] Dogfooding complete — `artifacts/qa-reports/dogfood-report.md` exists with 0 BLOCKING findings (run `/dogfood` if not done)
- [ ] `artifacts/docs/changelog.md` — 0 BLOCKING items
- [ ] `artifacts/issues/` — 0 open BLOCKING issues
- [ ] `npm run build` passes on current state

If any check fails: report to human, do not dispatch.

## Dispatch

Launch QA Agent subagent (foreground):

```
Task: Pre-Handoff Safety Audit

Read:
- .cursor/agents/qa-agent.md (your full instructions)
- .cursor/skills/security-audit/SKILL.md (security audit instructions)
- .cursor/rules/copy-rules.mdc (copy quality test for compliance check)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/tech-spec.md
- artifacts/docs/screen-specs-[app]-v1.md (interaction flows, credit costs for paywall gate integrity check)
- artifacts/docs/emotional-design-system.md (§6 dopamine specs for fidelity check)
- artifacts/docs/changelog.md

Mode: Pre-Handoff
Run the full pre-handoff audit: security audit (security-audit SKILL.md) + SPA-specific checks defined in your agent file's Pre-Handoff Mode.
Then run a final adversarial cross-check: challenge each finding — is it a real bug or a false positive?
Apply AUTO-FIX items directly. Escalate BLOCKING items to Tech Lead.
Signal completion when test: pre-handoff review complete is committed.
```

## Mobile pre-handoff additions (mode ≠ pwa)

If deployment mode is `native` or `pwa-then-native`, add these checks to the QA dispatch:

```
Additional mobile checks (append to Pre-Handoff audit):

1. Accessibility audit:
   - VoiceOver (iOS): navigate every screen with screen reader. Every interactive element must announce its role and label.
   - TalkBack (Android): same pass. Flag any silent or mis-labeled elements as BLOCKING.
   
2. Deep links:
   - Verify scheme://[path] opens the correct screen for every route in Expo Router
   - Verify auth-guarded deep links redirect to login then forward after auth
   
3. Push notifications (if §7c specifies push):
   - Verify token registration on fresh install
   - Verify notification received when sent via Expo Push Service test
   - Verify tap on notification navigates to correct screen
   
4. Biometrics (if §7c specifies local-authentication):
   - Verify Face ID / fingerprint prompt appears at configured trigger
   - Verify fallback to PIN/password works
   
5. Cross-platform rendering:
   - Every screen checked on both iOS Simulator and Android Emulator
   - Shadows, fonts, keyboard behavior, status bar verified on both
   
6. Offline behavior:
   - Disable network. App shows cached data or graceful error — no white screen or crash.
   - Re-enable network. Data refreshes automatically.
```

## After completion

**If clean (0 BLOCKING items):**
1. Update project-plan.md — mark pre-handoff complete
2. Present to human:

```
Pre-handoff audit complete. No blocking issues.

AUTO-FIX items applied: [N]
Informational findings logged: [N]

Ready for production deploy. Run /deploy when ready.
```

**If BLOCKING items found:**
1. Present findings to human
2. Create issues in `artifacts/issues/`
3. After fixes: re-run `/pre-handoff`
