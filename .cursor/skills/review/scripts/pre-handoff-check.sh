#!/bin/bash
# Pre-handoff automated checks — runs before the two-pass manual audit.
# Exit 0 = automated checks pass. Exit 1 = blocking issues found.
# Run from the project root.

BLOCKING=false

echo "=== Pre-Handoff Automated Checks ==="
echo ""

# 1. Final build
echo "[ ] Final build..."
npm run build 2>&1
if [ $? -ne 0 ]; then
  echo "BLOCKING: npm run build failed — fix before handoff"
  BLOCKING=true
else
  echo "PASS: Build clean"
fi
echo ""

# 2. TypeScript
echo "[ ] TypeScript..."
npx tsc --noEmit 2>&1
if [ $? -ne 0 ]; then
  echo "BLOCKING: TypeScript errors — fix before handoff"
  BLOCKING=true
else
  echo "PASS: TypeScript clean"
fi
echo ""

# 3. Check for hardcoded secrets patterns
echo "[ ] Hardcoded secrets scan..."
SECRETS=$(grep -rn \
  --include="*.ts" --include="*.tsx" \
  -E "(sk_live_|sk_test_|ANTHROPIC_API_KEY\s*=\s*['\"][^'\"]+|OPENAI_API_KEY\s*=\s*['\"][^'\"]+|service_role)" \
  src/ 2>/dev/null)
if [ -n "$SECRETS" ]; then
  echo "BLOCKING: Possible hardcoded secrets found:"
  echo "$SECRETS"
  BLOCKING=true
else
  echo "PASS: No hardcoded secrets detected"
fi
echo ""

# 4. Check for direct Supabase imports in route components (should use hooks/lib)
echo "[ ] Data access pattern check..."
BYPASS=$(grep -rn \
  --include="*.tsx" --include="*.ts" \
  "from.*@supabase/supabase-js" \
  src/routes/ src/components/ 2>/dev/null)
if [ -n "$BYPASS" ]; then
  echo "BLOCKING: Direct @supabase/supabase-js imports in routes/components (should use src/lib/supabase):"
  echo "$BYPASS"
  BLOCKING=true
else
  echo "PASS: Supabase client centralized"
fi
echo ""

# 5. Check for secrets in client-safe VITE_ env vars or build output
echo "[ ] Client-safe env var check..."
VITE_SECRETS=$(grep -rn \
  --include="*.ts" --include="*.tsx" --include="*.env*" \
  -E "VITE_.*(SECRET|SERVICE_ROLE|PRIVATE)" \
  . --exclude-dir=node_modules --exclude-dir=dist 2>/dev/null)
if [ -n "$VITE_SECRETS" ]; then
  echo "BLOCKING: Possible server-only secrets exposed via VITE_ prefix:"
  echo "$VITE_SECRETS"
  BLOCKING=true
else
  echo "PASS: No secrets in VITE_ vars"
fi

# 5b. Check build output for leaked secrets
if [ -d "dist" ] || [ -d "build" ]; then
  BUILD_DIR=$([ -d "build" ] && echo "build" || echo "dist")
  BUNDLE_SECRETS=$(grep -rl \
    -E "(SERVICE_ROLE|SUPABASE_SERVICE_ROLE_KEY|sk_live_|RESEND_API_KEY)" \
    "$BUILD_DIR/" 2>/dev/null)
  if [ -n "$BUNDLE_SECRETS" ]; then
    echo "BLOCKING: Server-only secrets found in build output:"
    echo "$BUNDLE_SECRETS"
    BLOCKING=true
  else
    echo "PASS: No secrets in build output"
  fi
fi
echo ""

# 6. Check changelog for blocking items
echo "[ ] Changelog blocking items..."
if [ -f "artifacts/docs/changelog.md" ]; then
  BLOCKING_ITEMS=$(grep -c "BLOCKING" artifacts/docs/changelog.md 2>/dev/null || echo "0")
  if [ "$BLOCKING_ITEMS" -gt 0 ]; then
    echo "BLOCKING: $BLOCKING_ITEMS BLOCKING item(s) in changelog — resolve before handoff"
    BLOCKING=true
  else
    echo "PASS: No BLOCKING items in changelog"
  fi
else
  echo "WARN: artifacts/docs/changelog.md not found"
fi
echo ""

# Summary
echo "=== Result ==="
if [ "$BLOCKING" = true ]; then
  echo "BLOCKING ISSUES FOUND — resolve before proceeding to manual audit"
  exit 1
else
  echo "AUTOMATED CHECKS PASSED — proceed to two-pass manual audit"
  exit 0
fi
