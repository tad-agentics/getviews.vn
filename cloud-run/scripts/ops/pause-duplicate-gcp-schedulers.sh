#!/usr/bin/env bash
# Pause GCP Cloud Scheduler jobs that duplicate Supabase pg_cron batch triggers.
#
# Keep pg_cron as the single source of truth (Vault URL + 52m timeout for ingest):
#   - cron-batch-ingest          0 20 * * * UTC  (03:00 ICT)
#   - cron-batch-morning-ritual  0 15 * * * UTC  (22:00 ICT)
#
# Retired duplicates (were firing the same Cloud Run paths 1h earlier / in parallel):
#   - getviews-corpus-ingest     02:00 ICT → POST /batch/ingest
#   - getviews-morning-ritual    22:00 ICT → POST /batch/morning-ritual
#
# Resume only if pg_cron is intentionally disabled:
#   gcloud scheduler jobs resume JOB --location=asia-southeast1
set -euo pipefail

LOCATION="${LOCATION:-asia-southeast1}"

for job in getviews-corpus-ingest getviews-morning-ritual; do
  echo "Pausing $job ($LOCATION)..."
  gcloud scheduler jobs pause "$job" --location="$LOCATION"
done

echo "Done. Verify: gcloud scheduler jobs list --location=$LOCATION"
