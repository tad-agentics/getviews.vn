#!/bin/bash
# Rule Validation — Test-Driven Rule Development
# Run after editing ANY .mdc rule, agent file, or command file.
# Tests that agent instructions are consistent, complete, and free of stale patterns.
# Exit 0 = all pass. Exit 1 = failures found.
#
# Usage: bash .cursor/skills/testing/scripts/validate-rules.sh

PASS=true
FAIL_COUNT=0
PASS_COUNT=0

fail() {
  echo "  FAIL: $1"
  PASS=false
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
}

check_zero() {
  # $1 = description, $2 = grep pattern, $3 = optional exclude pattern
  if [ -n "$3" ]; then
    count=$(grep -ri "$2" --include="*.md" --include="*.mdc" --include="*.example" 2>/dev/null | grep -v "$3" | wc -l)
  else
    count=$(grep -ri "$2" --include="*.md" --include="*.mdc" --include="*.example" 2>/dev/null | wc -l)
  fi
  if [ "$count" -gt 0 ]; then
    fail "$1 ($count hits)"
  else
    pass
  fi
}

check_positive() {
  # $1 = description, $2 = grep pattern, $3 = minimum count
  count=$(grep -rc "$2" --include="*.md" --include="*.mdc" 2>/dev/null | awk -F: '{s+=$2} END {print s}')
  if [ "$count" -lt "$3" ]; then
    fail "$1 (found $count, need $3+)"
  else
    pass
  fi
}

check_file_size() {
  # $1 = file, $2 = max lines
  lines=$(wc -l < "$1" 2>/dev/null)
  if [ "$lines" -gt "$2" ]; then
    fail "$1 is $lines lines (max $2)"
  else
    pass
  fi
}

echo "============================================"
echo "RULE VALIDATION — Test-Driven Checks"
echo "============================================"
echo ""

# ─── SECTION 1: BANNED PATTERNS (must be 0) ─────────────────────────

echo "── Banned Patterns ──"

check_zero "framer-motion (use 'motion' package)" \
  "framer-motion" \
  "Do not\|do not\|NOT\|never\|NEVER\|removed\|note intent\|rebuild in"

check_zero "HeroUI (removed — Make components only)" \
  "HeroUI" \
  "Do not\|do not\|NOT\|never\|removed"

check_zero "ANTHROPIC_API_KEY (use OPENROUTER_API_KEY)" \
  "ANTHROPIC_API_KEY" \
  "Do not install"

check_zero "NEXT_PUBLIC env vars (use VITE_ prefix)" \
  "NEXT_PUBLIC"

check_zero "@supabase/ssr (use @supabase/supabase-js)" \
  "@supabase/ssr"

check_zero "create-next-app (use create-react-router)" \
  "create-next-app"

check_zero "next build (use vite build)" \
  "next build"

check_zero "globals.css (use app.css)" \
  "globals\.css"

check_zero "Phase 6 (eliminated from RAD pipeline)" \
  "Phase 6" \
  "Polish\|verification\|screen building"

check_zero "get_design_context (Figma MCP forbidden in web context)" \
  "get_design_context" \
  "Do not\|do not\|NOT\|never\|would cause\|optional\|Use MCP when\|delivery mechanism\|returns.*source files"

check_zero "stale 'ported into' language (use 'copied into')" \
  "ported into\|Ported into" \
  "Figma Make Porting\|off-limits during porting"

echo ""

# ─── SECTION 2: REQUIRED PATTERNS (must be present) ─────────────────

echo "── Copy-Then-Edit Enforcement ──"

check_positive "COPY / copy file directly" \
  "COPY\|copy.*file.*direct\|cp src/make-import" 10

check_positive "str_replace as edit method" \
  "str_replace" 10

check_positive "'90% untouched' rule" \
  "90%" 3

check_positive "'Never rewrite' enforcement" \
  "Never rewrite\|Do NOT rewrite" 3

echo ""
echo "── TanStack React Query ──"

check_positive "TanStack / react-query mentioned" \
  "TanStack\|tanstack/react-query\|React Query" 10

check_positive "staleTime configuration" \
  "staleTime" 5

check_positive "queryKeys convention" \
  "queryKeys\|query-keys" 3

check_positive "useCredits shared hook" \
  "useCredits" 3

check_positive "invalidateQueries in mutations" \
  "invalidateQueries" 3

echo ""
echo "── LLM via OpenRouter ──"

check_positive "OPENROUTER_API_KEY referenced" \
  "OPENROUTER_API_KEY" 4

check_positive "OpenRouter mentioned" \
  "OpenRouter\|openrouter" 8

check_positive "llm_cache table" \
  "llm_cache" 3

check_positive "supabase.functions.invoke for Edge Function calls" \
  "functions\.invoke" 3

echo ""
echo "── Edge Function CORS ──"

check_positive "corsHeaders in code patterns" \
  "corsHeaders" 5

check_positive "OPTIONS preflight handler" \
  "OPTIONS" 3

check_positive "_shared/cors.ts referenced" \
  "_shared/cors" 3

echo ""
echo "── Visual Fidelity ──"

check_positive "IDENTICAL / BLOCKING fidelity checks" \
  "IDENTICAL\|every deviation.*BLOCKING\|visual diff.*bug" 2

check_positive "'What NEVER changes' enforcement" \
  "NEVER changes\|off-limits" 2

echo ""
echo "── QA Adversarial Passes ──"

check_positive "5-pass QA structure" \
  "Pass 1\|Pass 2\|Pass 3\|Pass 4\|Pass 5" 5

check_positive "Adversarial cross-check" \
  "adversarial cross-check\|false positive\|strip false" 2

echo ""

# ─── SECTION 3: STACK CONSISTENCY ────────────────────────────────────

echo "── Stack Line Consistency ──"

# All stack declaration lines must include TanStack React Query
stack_lines=$(grep -rn "^Stack:\|^React Router v7 (Vite) ·" --include="*.md" --include="*.mdc" | wc -l)
stack_with_tanstack=$(grep -rn "^Stack:\|^React Router v7 (Vite) ·" --include="*.md" --include="*.mdc" | grep -c "TanStack")

if [ "$stack_lines" -gt 0 ] && [ "$stack_with_tanstack" -lt "$stack_lines" ]; then
  fail "Some stack lines missing TanStack React Query ($stack_with_tanstack/$stack_lines)"
else
  pass
fi

echo ""

# ─── SECTION 4: FOUNDATION STEP CONSISTENCY ──────────────────────────

echo "── Foundation Step Numbering ──"

agent_steps=$(grep -c "^\*\*Step [0-9]" .cursor/agents/frontend-developer.md 2>/dev/null)
command_steps=$(grep -c "^Step [0-9]" .cursor/commands/foundation.md 2>/dev/null)

if [ "$agent_steps" -ne "$command_steps" ]; then
  fail "Frontend agent has $agent_steps steps but foundation.md has $command_steps steps"
else
  pass
fi

echo ""

# ─── SECTION 5: .MDC FILE SIZE LIMITS ───────────────────────────────

echo "── File Size Limits ──"

for f in .cursor/rules/*.mdc; do
  check_file_size "$f" 500
done

echo ""

# ─── SECTION 6: DATA FETCHING ANTI-PATTERNS ─────────────────────────

echo "── Data Fetching Rules ──"

# useState+useEffect as ALLOWED for data fetching (should be 0)
allowed_raw=$(grep -rn "useState.*useEffect" --include="*.md" --include="*.mdc" 2>/dev/null | grep -v "forbidden\|WRONG\|Never\|never\|No Raw\|❌\|FAIL\|flag" | wc -l)
if [ "$allowed_raw" -gt 1 ]; then
  fail "useState+useEffect appears as allowed pattern ($allowed_raw hits — should be forbidden)"
else
  pass
fi

# Raw supabase.from('profiles') in screen context (should be forbidden)
profiles_positive=$(grep -rn "supabase\.from.*profiles" --include="*.md" --include="*.mdc" 2>/dev/null | grep -v "never\|Never\|flag\|BLOCKING\|do not\|Do not\|no screen\|No screen" | wc -l)
if [ "$profiles_positive" -gt 0 ]; then
  fail "Direct supabase.from('profiles') appears as allowed pattern ($profiles_positive hits)"
else
  pass
fi

echo ""

# ─── SECTION 7: STALENESS CHECKS ─────────────────────────────────────

echo "── Staleness & Cross-Reference Checks ──"

# Shared protocols reference in all agent files
for agent in .cursor/agents/*.md; do
  agent_name=$(basename "$agent")
  if ! grep -q "Shared protocols" "$agent" 2>/dev/null; then
    fail "$agent_name missing 'Shared protocols' section (AskUserQuestion + Completion Status)"
  else
    pass
  fi
done

# ETHOS.md exists and is referenced
if [ ! -f "artifacts/docs/ETHOS.md" ]; then
  fail "artifacts/docs/ETHOS.md missing — builder ethos not defined"
else
  pass
fi

if ! grep -q "ETHOS.md" .cursor/rules/project.mdc 2>/dev/null; then
  fail "project.mdc does not reference ETHOS.md"
else
  pass
fi

# investigate skill exists
if [ ! -f ".cursor/skills/investigate/SKILL.md" ]; then
  fail "investigate skill missing at .cursor/skills/investigate/SKILL.md"
else
  pass
fi

# qa-reports directory exists
if [ ! -d "artifacts/qa-reports" ]; then
  fail "artifacts/qa-reports/ directory missing — QA health scores have no output location"
else
  pass
fi

# hooks.json has destructive command check
if [ -f ".cursor/hooks.json" ]; then
  if ! grep -q "check-destructive" .cursor/hooks.json 2>/dev/null; then
    fail "hooks.json missing destructive command guardrail (check-destructive.sh)"
  else
    pass
  fi
fi

# Agent files reference stale paths — catch references to deleted files
stale_path_hits=$(grep -rn "src/make-import/" --include="*.md" --include="*.mdc" 2>/dev/null | grep -v "copy\|Copy\|COPY\|make-import.*temporary\|deleted after\|human copies\|Read.*make-import\|cp src\|catalogs\|Source\|dump\|compare\|import/" | wc -l)
if [ "$stale_path_hits" -gt 15 ]; then
  fail "Excessive references to src/make-import/ outside of copy context ($stale_path_hits hits — may be stale after porting)"
else
  pass
fi

# Phase 1 skill exists
if [ ! -f ".cursor/skills/phase1/SKILL.md" ]; then
  fail "Phase 1 skill missing at .cursor/skills/phase1/SKILL.md — northstar template not available"
else
  pass
fi

# /office-hours references northstar validation (not optional)
if grep -q "optional" .cursor/commands/office-hours.md 2>/dev/null; then
  fail "/office-hours still marked as optional — should be mandatory gate"
else
  pass
fi

# /dogfood command exists
if [ ! -f ".cursor/commands/dogfood.md" ]; then
  fail "/dogfood command missing — no structured product testing step"
else
  pass
fi

# Tech spec skill references data invariants
if ! grep -q "invariant" .cursor/skills/tech-spec/SKILL.md 2>/dev/null; then
  fail "tech-spec SKILL.md missing data invariants step"
else
  pass
fi

# Tech spec skill has anti-pattern checklist
if ! grep -q "Anti-Pattern Checklist" .cursor/skills/tech-spec/SKILL.md 2>/dev/null; then
  fail "tech-spec SKILL.md missing schema anti-pattern checklist"
else
  pass
fi

# Architecture skill exists
if [ ! -f ".cursor/skills/architecture/SKILL.md" ]; then
  fail "Architecture skill missing at .cursor/skills/architecture/SKILL.md — Tech Lead has no stack constraint reference"
else
  pass
fi

# Architecture skill has complexity signals
if ! grep -q "Complexity Signal" .cursor/skills/architecture/SKILL.md 2>/dev/null; then
  fail "Architecture skill missing complexity signals section"
else
  pass
fi

# Architecture skill has stack constraints
if ! grep -q "Stack Constraints" .cursor/skills/architecture/SKILL.md 2>/dev/null; then
  fail "Architecture skill missing stack constraints section"
else
  pass
fi

# /office-hours references stack fit check
if ! grep -q "Stack fit" .cursor/commands/office-hours.md 2>/dev/null; then
  fail "/office-hours missing stack fit check — product requirements not validated against stack limits"
else
  pass
fi

# Research agent supports Mode 2 (technical pattern research)
if ! grep -q "Mode 2" .cursor/agents/research-agent.md 2>/dev/null; then
  fail "Research agent missing Mode 2 — no technical pattern research capability"
else
  pass
fi

# Tech spec skill references complexity scan
if ! grep -q "complexity" .cursor/skills/tech-spec/SKILL.md 2>/dev/null; then
  fail "tech-spec SKILL.md missing complexity scan step — features not checked for non-trivial patterns"
else
  pass
fi

# Tech spec skill has technical decisions template
if ! grep -q "TD-\[N\]\|Technical Decision" .cursor/skills/tech-spec/SKILL.md 2>/dev/null; then
  fail "tech-spec SKILL.md missing technical decisions template"
else
  pass
fi

echo ""

# ─── SECTION 8: MOBILE CHECKS (conditional — only if mobile/ exists) ──

if [ -d "mobile" ]; then
  echo "── Mobile Structure ──"

  # Workspace config (skip if project not yet initialized — workspaces added during /init Step 5b)
  if [ -d "node_modules" ]; then
    if ! grep -q '"workspaces"' package.json 2>/dev/null; then
      fail "Root package.json missing workspaces field"
    else
      pass
    fi
  else
    pass  # template state — /init hasn't run yet
  fi

  # Shared structure (uses check_file_size pattern — file must exist and be non-empty)
  for f in shared/package.json shared/index.ts shared/colors.ts shared/api/supabase.ts shared/api/supabase-context.ts; do
    if [ ! -f "$f" ]; then
      fail "Missing: $f"
    else
      pass
    fi
  done

  # Mobile structure
  for f in mobile/app.config.ts mobile/eas.json mobile/metro.config.js mobile/tailwind.config.js mobile/global.css; do
    if [ ! -f "$f" ]; then
      fail "Missing: $f"
    else
      pass
    fi
  done

  # Agent + rules
  for f in .cursor/agents/mobile-developer.md .cursor/rules/mobile.mdc; do
    if [ ! -f "$f" ]; then
      fail "Missing: $f"
    else
      pass
    fi
  done

  echo ""
  echo "── Mobile Cross-Import Guard ──"

  # No cross-imports
  src_imports_mobile=$(grep -rn "from.*\.\./mobile\|from.*mobile/" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
  if [ "$src_imports_mobile" -gt 0 ]; then
    fail "src/ imports from mobile/ ($src_imports_mobile hits)"
  else
    pass
  fi

  mobile_imports_src=$(grep -rn "from.*\.\./src/" mobile/ --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
  if [ "$mobile_imports_src" -gt 0 ]; then
    fail "mobile/ imports from src/ ($mobile_imports_src hits)"
  else
    pass
  fi

  shared_imports_platform=$(grep -rn "from.*/src/\|from.*/mobile/" shared/ --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
  if [ "$shared_imports_platform" -gt 0 ]; then
    fail "shared/ imports from src/ or mobile/ ($shared_imports_platform hits)"
  else
    pass
  fi

  echo ""
  echo "── Mobile .mdc Size ──"

  check_file_size ".cursor/rules/mobile.mdc" 500

  echo ""
  echo "── Mobile Prohibitions ──"

  # mobile.mdc must have NEVER rules
  check_positive "NEVER prohibitions in mobile.mdc" \
    "NEVER" 10

  # NativeWind preset in tailwind config
  if ! grep -q "nativewind/preset" mobile/tailwind.config.js 2>/dev/null; then
    fail "mobile/tailwind.config.js missing nativewind/preset"
  else
    pass
  fi

  echo ""
else
  echo "── Mobile: SKIPPED (no mobile/ directory — pwa mode) ──"
  echo ""
fi

# ─── SUMMARY ─────────────────────────────────────────────────────────

echo "============================================"
if [ "$PASS" = true ]; then
  echo "ALL $PASS_COUNT CHECKS PASSED"
  exit 0
else
  echo "$FAIL_COUNT FAILED / $((PASS_COUNT + FAIL_COUNT)) total"
  echo "Fix failing checks before proceeding."
  exit 1
fi
