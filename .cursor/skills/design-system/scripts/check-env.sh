#!/bin/bash
# Verify UI_REFERENCE_REPO is set before Phase 3 can proceed.
# Exit 0 = OK to continue. Exit 1 = hard stop, report to human.

if [ -z "$UI_REFERENCE_REPO" ]; then
  echo "ERROR: UI_REFERENCE_REPO is not set."
  echo ""
  echo "Add it to .env.local:"
  echo "  UI_REFERENCE_REPO=owner/repo-name"
  echo ""
  echo "Then re-run /phase3."
  exit 1
fi

echo "OK: UI_REFERENCE_REPO=$UI_REFERENCE_REPO"
exit 0
