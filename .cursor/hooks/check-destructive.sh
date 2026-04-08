#!/bin/bash
# .cursor/hooks/check-destructive.sh
# PreToolUse hook: warns before destructive shell commands.
# Reads the command from stdin (Cursor passes tool input as JSON).
# Returns exit 0 to allow, exit 2 to block with message.

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command string from JSON (handles both "command" and "cmd" keys)
CMD=$(echo "$INPUT" | grep -oE '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/"command"\s*:\s*"//' | sed 's/"$//')
if [ -z "$CMD" ]; then
  CMD=$(echo "$INPUT" | grep -oE '"cmd"\s*:\s*"[^"]*"' | head -1 | sed 's/"cmd"\s*:\s*"//' | sed 's/"$//')
fi

# If we can't extract a command, allow it
[ -z "$CMD" ] && exit 0

# Safe exceptions — common dev cleanup
case "$CMD" in
  *"rm -rf node_modules"*|*"rm -rf .next"*|*"rm -rf dist"*|*"rm -rf build"*)
    exit 0 ;;
  *"rm -rf __pycache__"*|*"rm -rf .cache"*|*"rm -rf .turbo"*|*"rm -rf coverage"*)
    exit 0 ;;
  *"rm -rf .vercel"*|*"rm -rf .supabase"*)
    exit 0 ;;
esac

# Destructive patterns
WARN=""

case "$CMD" in
  *"rm -rf"*|*"rm -r "*|*"rm --recursive"*)
    WARN="DESTRUCTIVE: recursive delete detected ($CMD). This permanently removes files." ;;
  *"DROP TABLE"*|*"DROP DATABASE"*|*"TRUNCATE"*)
    WARN="DESTRUCTIVE: SQL data destruction detected. This permanently deletes data." ;;
  *"git push --force"*|*"git push -f "*|*"git push "*"-f"*)
    WARN="DESTRUCTIVE: force push rewrites remote history. Other collaborators may lose work." ;;
  *"git reset --hard"*)
    WARN="DESTRUCTIVE: hard reset discards all uncommitted changes permanently." ;;
  *"supabase db reset"*|*"supabase db push"*)
    # db reset is expected in dev; db push is expected in deploy — just note it
    exit 0 ;;
esac

if [ -n "$WARN" ]; then
  echo "$WARN"
  echo "Confirm this is intentional before proceeding."
  exit 2
fi

exit 0
