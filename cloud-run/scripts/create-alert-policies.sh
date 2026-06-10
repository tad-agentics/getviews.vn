#!/usr/bin/env bash
# Production alerting bootstrap (audit 2026-06-10 H-1).
#
# Before this, the only alert in the system was the pg_net batch 4xx watch —
# Cloud Run 5xx spikes, payment-webhook failures, and failed credit refunds
# were invisible until a customer complained.
#
# Usage:
#   GCP_PROJECT_ID=my-project NOTIFY_EMAIL=ops@getviews.vn ./create-alert-policies.sh
#
# Idempotent-ish: re-running creates duplicate policies — check
# `gcloud alpha monitoring policies list` first.
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
NOTIFY_EMAIL="${NOTIFY_EMAIL:?Set NOTIFY_EMAIL (alert destination)}"

echo "Creating notification channel for $NOTIFY_EMAIL ..."
CHANNEL=$(gcloud beta monitoring channels create \
  --project "$PROJECT_ID" \
  --display-name "GetViews ops email" \
  --type email \
  --channel-labels "email_address=$NOTIFY_EMAIL" \
  --format "value(name)")
echo "Channel: $CHANNEL"

# 1. Log-based metric + alert: credit refund failures (manual compensation needed).
#    Matches getviews_pipeline/credits.py "REFUND FAILED" ERROR line.
echo "Creating log-based metric refund_failed ..."
gcloud logging metrics create refund_failed \
  --project "$PROJECT_ID" \
  --description "Credit refund RPC failed after a paid pipeline error — compensate manually" \
  --log-filter 'resource.type="cloud_run_revision" severity>=ERROR textPayload:"REFUND FAILED"' \
  || echo "(metric exists — ok)"

cat > /tmp/policy-refund-failed.json <<EOF
{
  "displayName": "Credit refund failed (manual compensation needed)",
  "combiner": "OR",
  "conditions": [{
    "displayName": "refund_failed > 0 in 5m",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/refund_failed\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 0,
      "duration": "0s",
      "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_SUM"}]
    }
  }],
  "notificationChannels": ["$CHANNEL"]
}
EOF
gcloud alpha monitoring policies create --project "$PROJECT_ID" --policy-from-file /tmp/policy-refund-failed.json

# 2. Cloud Run 5xx rate on the user pod (paid SSE paths).
cat > /tmp/policy-5xx.json <<EOF
{
  "displayName": "Cloud Run user pod 5xx spike",
  "combiner": "OR",
  "conditions": [{
    "displayName": "5xx > 5/min for 5m",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"getviews-pipeline-user\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 5,
      "duration": "300s",
      "aggregations": [{"alignmentPeriod": "60s", "perSeriesAligner": "ALIGN_RATE"}]
    }
  }],
  "notificationChannels": ["$CHANNEL"]
}
EOF
gcloud alpha monitoring policies create --project "$PROJECT_ID" --policy-from-file /tmp/policy-5xx.json

# 3. Gemini daily budget cap hit (calls being refused).
echo "Creating log-based metric gemini_budget_block ..."
gcloud logging metrics create gemini_budget_block \
  --project "$PROJECT_ID" \
  --description "Gemini daily USD cap reached — paid analyses are being refused" \
  --log-filter 'resource.type="cloud_run_revision" severity>=ERROR textPayload:"refusing call"' \
  || echo "(metric exists — ok)"

cat > /tmp/policy-budget.json <<EOF
{
  "displayName": "Gemini daily budget cap hit",
  "combiner": "OR",
  "conditions": [{
    "displayName": "budget blocks > 0 in 5m",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/gemini_budget_block\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 0,
      "duration": "0s",
      "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_SUM"}]
    }
  }],
  "notificationChannels": ["$CHANNEL"]
}
EOF
gcloud alpha monitoring policies create --project "$PROJECT_ID" --policy-from-file /tmp/policy-budget.json

echo ""
echo "Done. Note: PayOS webhook errors live in Supabase Edge Function logs"
echo "(Dashboard → Edge Functions → payos-webhook) — Supabase has no alert API"
echo "yet; check the function's error rate weekly or pipe logs to GCP."
