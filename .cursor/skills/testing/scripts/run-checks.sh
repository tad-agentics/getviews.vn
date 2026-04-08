#!/bin/bash
# Run build and type checks for feature QA.
# Exit 0 = all pass. Exit 1 = failures found.
# Run from the project root.

PASS=true

echo "=== Feature QA — Build Checks ==="
echo ""

# 1. TypeScript type check
echo "[ ] TypeScript..."
npx tsc --noEmit 2>&1
if [ $? -ne 0 ]; then
  echo "FAIL: TypeScript errors found"
  PASS=false
else
  echo "PASS: TypeScript clean"
fi
echo ""

# 2. Build
echo "[ ] Vite build..."
npm run build 2>&1
if [ $? -ne 0 ]; then
  echo "FAIL: npm run build failed"
  PASS=false
else
  echo "PASS: Build succeeded"
fi
echo ""

# 3. Lint
echo "[ ] ESLint..."
npm run lint 2>&1
if [ $? -ne 0 ]; then
  echo "WARN: Lint warnings/errors found (check output above)"
else
  echo "PASS: Lint clean"
fi
echo ""

# 4. Test suite
echo "[ ] Vitest..."
npm test 2>&1
if [ $? -ne 0 ]; then
  echo "FAIL: Test suite failures found"
  PASS=false
else
  echo "PASS: All tests pass"
fi
echo ""

# Summary
echo "=== Result ==="
if [ "$PASS" = true ]; then
  echo "ALL CHECKS PASSED — ready for QA review"
  exit 0
else
  echo "CHECKS FAILED — fix errors before marking feature complete"
  exit 1
fi
