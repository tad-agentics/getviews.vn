#!/bin/bash
# .cursor/hooks/on-agent-stop.sh
# Runs when Cursor agent finishes a session.
# Auto-validates .mdc rules and runs build check.
# Reads stdin JSON payload from Cursor (ignored — we just need the project root).

# Navigate to project root (hooks.json is in .cursor/, so parent is root)
cd "$(dirname "$0")/.." || exit 0

# 1. Validate rules (only if validate-rules.sh exists)
if [ -f ".cursor/skills/testing/scripts/validate-rules.sh" ]; then
  echo ""
  echo "=== Post-Agent: Rule Validation ==="
  bash .cursor/skills/testing/scripts/validate-rules.sh 2>&1 | tail -5
fi

# 2. Build check
if [ -f "package.json" ]; then
  echo ""
  echo "=== Post-Agent: Build Check ==="
  npm run build --silent 2>&1 | tail -3
  if [ $? -eq 0 ]; then
    echo "BUILD: OK"
  else
    echo "BUILD: FAILED — check errors above"
  fi
fi
