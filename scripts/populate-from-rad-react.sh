#!/usr/bin/env bash
# Copy RAD-React template files into a new project directory (your app repo).
# Does not add or change remotes — use your own GitHub repo for commits.
set -euo pipefail

TEMPLATE_URL="${RAD_REACT_TEMPLATE_URL:-https://github.com/tad-agentics/RAD-React.git}"

FORCE=false

usage() {
  cat <<'EOF'
Copy files from the RAD-React template repo into a target folder (e.g. a new app repo).

Usage: populate-from-rad-react.sh [--force] [target-directory]

  target-directory   Where to copy files (default: current directory).
  --force            Allow a non-empty target (merges template; does not delete your extra files).

Environment:
  RAD_REACT_TEMPLATE_URL   Git clone URL (default: https://github.com/tad-agentics/RAD-React.git)
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage ;;
    --force) FORCE=true; shift ;;
    *) break ;;
  esac
done

TARGET=${1:-.}
TARGET=$(cd "$TARGET" && pwd)

if [[ "$FORCE" != true ]]; then
  if find "$TARGET" -mindepth 1 -maxdepth 1 ! -name '.git' 2>/dev/null | grep -q .; then
    echo "Error: target is not empty (files other than .git). Empty it or pass --force." >&2
    exit 1
  fi
fi

TMP=$(mktemp -d)
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

if [[ -n "${RAD_REACT_TEMPLATE_BRANCH:-}" ]]; then
  git clone --depth 1 --branch "$RAD_REACT_TEMPLATE_BRANCH" "$TEMPLATE_URL" "$TMP/rad"
else
  git clone --depth 1 "$TEMPLATE_URL" "$TMP/rad"
fi

echo "Copying template into: $TARGET"
rsync -a --exclude='.git' "$TMP/rad/" "$TARGET/"

echo "Done. Next: set git remote to your app repo, commit, open in Cursor. Do not push to tad-agentics/RAD-React."
