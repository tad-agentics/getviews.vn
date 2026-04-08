#!/bin/bash
# Fetch and decode a screenshot from the UI reference library.
# Usage: ./fetch-screenshot.sh <ID>
# Output: saves decoded PNG to /tmp/ref-<ID>.png
# Requires: UI_REFERENCE_REPO env var, curl, jq

ID="$1"

if [ -z "$ID" ]; then
  echo "Usage: $0 <screenshot-id>" >&2
  echo "Example: $0 047" >&2
  exit 1
fi

if [ -z "$UI_REFERENCE_REPO" ]; then
  echo "ERROR: UI_REFERENCE_REPO is not set. Run check-env.sh first." >&2
  exit 1
fi

OUTPUT="/tmp/ref-${ID}.png"

curl -s \
  "https://api.github.com/repos/$UI_REFERENCE_REPO/contents/main/screenshots/${ID}.png" \
  -H "Accept: application/vnd.github.v3+json" \
  | jq -r '.content' \
  | base64 -d > "$OUTPUT"

if [ $? -eq 0 ] && [ -s "$OUTPUT" ]; then
  echo "OK: Screenshot saved to $OUTPUT"
  exit 0
else
  echo "ERROR: Failed to fetch screenshot $ID from $UI_REFERENCE_REPO" >&2
  exit 1
fi
