---
name: security-audit
description: Security audit — OWASP Top 10 + Supabase-specific checks + dependency supply chain scan. Run during pre-handoff before deploying to production.
disable-model-invocation: true
---

# Security Audit — Pre-Deploy Safety Check

Run this during pre-handoff, before the DevOps agent deploys. Two modes:

- **Standard (default):** High-confidence findings only (8/10 confidence gate). Zero false positives tolerated.
- **Comprehensive (`--comprehensive`):** Lower bar (2/10). Monthly deep scan. Includes informational findings.

## Phase 1 — Secrets Archaeology

Scan the entire repo history for leaked secrets:

```bash
# Check current codebase for secrets
grep -rn "sk_live_\|sk-or-\|re_\|whsec_\|SUPABASE_SERVICE_ROLE_KEY\s*=" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.env*" . 2>/dev/null | grep -v node_modules | grep -v ".env.example"

# Check git history for secrets that were committed then removed
git log --all --diff-filter=D -p -- "*.env" "*.env.local" 2>/dev/null | grep -E "sk_live_|sk-or-|re_|whsec_|SERVICE_ROLE" | head -20

# Check build output for leaked secrets
if [ -d "dist" ] || [ -d "build" ]; then
  grep -rn "SERVICE_ROLE\|sk-or-\|sk_live_\|re_\|whsec_" dist/ build/ 2>/dev/null
fi
```

**BLOCKING** if any secret found in current code or build output.
**INFORMATIONAL** if found in git history (recommend `git filter-repo` cleanup).

## Phase 2 — Dependency Supply Chain

```bash
# Check for known vulnerabilities
npm audit --production 2>/dev/null || echo "npm audit failed"

# Check for suspicious packages (typosquatting, very new, low download count)
# Look at direct dependencies only
cat package.json | grep -A 100 '"dependencies"' | grep -B 100 '}'
```

**BLOCKING** if `npm audit` shows critical or high severity.
**INFORMATIONAL** for moderate/low.

## Phase 3 — Supabase RLS Verification

```bash
# List all tables and their RLS status
# Must be run with Supabase MCP or local supabase CLI
supabase db lint 2>/dev/null || echo "Run 'supabase db lint' manually"
```

Manual checks:
- Every table in `supabase/migrations/` has `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- No RLS policy uses `USING (true)` on user-owned tables (public read-only tables like enums are OK)
- SELECT policies filter by `auth.uid() = user_id`
- INSERT policies enforce `auth.uid() = user_id` (no client-side user_id injection)
- UPDATE/DELETE policies scope to owner: `USING (auth.uid() = user_id)`
- No table has RLS disabled after being enabled

**BLOCKING** if any user-data table missing RLS or has `USING (true)`.

## Phase 4 — Edge Function Security

For each Edge Function in `supabase/functions/`:

1. **CORS check** — imports `corsHeaders` from `_shared/cors.ts`, handles OPTIONS preflight
2. **Input validation** — uses zod or equivalent for all request body parsing
3. **No secrets in response** — grep function code for any pattern that returns API keys, service role keys, or internal URLs
4. **Webhook signature verification** — any function named `*-webhook` must verify signatures before processing
5. **Error handling** — no raw exception stack traces returned to caller

**BLOCKING** if missing CORS, missing input validation, or secrets in response.

## Phase 5 — OWASP Top 10 (Web Application)

Check against OWASP Top 10 2021 categories relevant to this stack:

| # | Category | What to check | Where |
|---|---|---|---|
| A01 | Broken Access Control | RLS policies, auth guard on all /app routes, direct URL access to other users' data | Phase 3 + frontend routes |
| A02 | Cryptographic Failures | HTTPS only, no plaintext secrets in localStorage, secure cookie flags | Frontend code |
| A03 | Injection | SQL injection via raw queries (should use Supabase client), XSS via dangerouslySetInnerHTML | Frontend + Edge Functions |
| A05 | Security Misconfiguration | Default Supabase keys, verbose error messages, debug mode in production | `.env.example` + build config |
| A07 | Auth Failures | Session handling, token expiry, OAuth callback validation | Auth flow |
| A09 | Logging & Monitoring | No sensitive data in console.log, error boundaries don't leak info | Frontend code |

```bash
# A03 — Check for raw SQL or innerHTML
grep -rn "dangerouslySetInnerHTML\|\.raw\s*(" --include="*.tsx" --include="*.ts" src/ 2>/dev/null | grep -v node_modules

# A05 — Check for debug/development flags in production config
grep -rn "debug.*true\|NODE_ENV.*development" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | grep -v node_modules | grep -v "test"

# A09 — Check for sensitive data logging
grep -rn "console\.log.*password\|console\.log.*token\|console\.log.*secret\|console\.log.*key" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | grep -v node_modules
```

## Final — Report

Write findings to `artifacts/qa-reports/security-audit-YYYY-MM-DD.md`:

```markdown
# Security Audit — [date]

**Mode:** Standard | Comprehensive
**Findings:** [N BLOCKING, M INFORMATIONAL]

## BLOCKING (must fix before deploy)
- [finding with exact file:line and remediation]

## INFORMATIONAL (fix when convenient)
- [finding]

## Checks Passed
- [ ] No secrets in current code or build output
- [ ] npm audit: 0 critical/high
- [ ] RLS on all user-data tables
- [ ] Edge Functions: CORS + validation + no secret leakage
- [ ] OWASP: no injection, no auth bypass, no misconfig

## Verdict
PASS — safe to deploy | BLOCKED — [N] items must be fixed first
```

For each BLOCKING finding, classify as AUTO-FIX (apply directly) or ESCALATE (requires Tech Lead decision). Apply AUTO-FIX items with atomic commits: `fix(security): [description]`.
