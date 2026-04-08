#!/bin/bash
# Fetch and decode the UI reference library index from GitHub Contents API.
# Outputs the decoded index.md content to stdout.
# Requires: UI_REFERENCE_REPO env var, curl, jq

if [ -z "$UI_REFERENCE_REPO" ]; then
  echo "ERROR: UI_REFERENCE_REPO is not set. Run check-env.sh first." >&2
  exit 1
fi

curl -s \
  "https://api.github.com/repos/$UI_REFERENCE_REPO/contents/main/index.md" \
  -H "Accept: application/vnd.github.v3+json" \
  | jq -r '.content' \
  | base64 -d
