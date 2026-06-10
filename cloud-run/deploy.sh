#!/usr/bin/env bash
#
# Deploy the GetViews Cloud Run pipeline.
#
# Two services share one image (selected by SERVICE_ROLE env var so live
# user SSE traffic and 30-minute cron batches don't share quota or
# scaling pressure):
#
#   getviews-pipeline-user  — user-facing routes; min:1, 2Gi, 300s
#   getviews-pipeline-batch — /batch/* + /admin/*; min:0, 4Gi, 3600s
#
# Usage:
#   ./deploy.sh                   # build + deploy both services
#   ./deploy.sh user              # build + deploy user only
#   ./deploy.sh batch             # build + deploy batch only
#   SKIP_BUILD=1 ./deploy.sh ...  # reuse image (after CI build — see cloud-run/docs/ci-cloud-run-build.md)
#
# Project: set GCP_PROJECT_ID or ``gcloud config set project ID`` (active
# config is used when GCP_PROJECT_ID is unset).
#
set -euo pipefail

if [[ -n "${GCP_PROJECT_ID:-}" ]]; then
  PROJECT_ID="${GCP_PROJECT_ID//[[:space:]]/}"
else
  PROJECT_ID="$(gcloud config get-value project 2>/dev/null | tr -d '[:space:]')"
fi
if [[ -z "$PROJECT_ID" ]]; then
  echo "Missing project: set GCP_PROJECT_ID or run gcloud config set project YOUR_PROJECT_ID" >&2
  exit 2
fi
REGION="${REGION:-asia-southeast1}"   # Singapore — lowest latency to Vietnam
IMAGE="gcr.io/$PROJECT_ID/getviews-pipeline"

TARGET="${1:-both}"
case "$TARGET" in
  user|batch|both) ;;
  *)
    echo "Unknown target: $TARGET (expected: user | batch | both)" >&2
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "Building image $IMAGE (context: repo root — .gcloudignore keeps upload small)..."
  gcloud builds submit --project "$PROJECT_ID" \
    --config="$SCRIPT_DIR/cloudbuild.yaml" \
    --substitutions="_TAG=$IMAGE" \
    "$REPO_ROOT"
else
  echo "SKIP_BUILD=1 — reusing existing image $IMAGE (built by CI or a prior local submit)"
fi

# IMPORTANT — env-var preservation across image-rebuild deploys.
#
# Prior versions of this script passed ``--update-env-vars SERVICE_ROLE=…``
# to ``gcloud run deploy --image …`` and asserted in the comments that
# this preserved the other env vars on the service. In practice it does
# NOT — ``gcloud run deploy --image`` + any env-mutation flag emits a
# fresh revision whose env block contains only the listed vars + the
# service-default SERVICE_ROLE. On 2026-05-17 this silently wiped the
# batch pod from 20 env vars down to 1 (BATCH_SECRET, SUPABASE_*,
# GEMINI_API_KEY, R2_*, etc. all gone). The next nightly batch ingest
# would have hard-failed.
#
# Fix: do the deploy WITHOUT any env-mutation flag (so gcloud keeps the
# existing env block intact), then issue a follow-up
# ``gcloud run services update --update-env-vars SERVICE_ROLE=…`` to
# pin the role. ``services update --update-env-vars`` is genuinely
# additive — it merges with the existing env block.
deploy_user() {
  # User-facing pod: needs 1 warm instance for snappy first-token SSE.
  # 900s timeout: Gemini video analysis caps at ~120s per call, but a
  # compare turn (2 deep diagnoses) + synthesis + a slow client reading
  # the SSE stream can stack well past the old 600s — the request
  # timeout covers the whole stream lifetime, not just compute.
  # Smaller memory than batch since one request streams one video,
  # not a corpus wave.
  echo ""
  echo "Deploying getviews-pipeline-user..."
  gcloud run deploy getviews-pipeline-user \
    --project "$PROJECT_ID" \
    --image "$IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 900 \
    --concurrency 20 \
    --min-instances 1 \
    --max-instances 5
  echo "Pinning SERVICE_ROLE=user (additive update, preserves all other env vars)..."
  gcloud run services update getviews-pipeline-user \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --update-env-vars "SERVICE_ROLE=user"
}

deploy_batch() {
  # Batch pod: cold-starts are fine (Cloud Scheduler tolerates startup
  # latency). 8Gi — HI-13 Batch JSONL + parallel MP4 prep exceeded 4Gi in prod (OOM ~4.1Gi).
  # 3600s timeout because all-niche ingest can run 10–30+ minutes.
  echo ""
  echo "Deploying getviews-pipeline-batch..."
  gcloud run deploy getviews-pipeline-batch \
    --project "$PROJECT_ID" \
    --image "$IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 8Gi \
    --cpu 2 \
    --timeout 3600 \
    --concurrency 5 \
    --min-instances 0 \
    --max-instances 3
  echo "Pinning SERVICE_ROLE=batch (additive update, preserves all other env vars)..."
  gcloud run services update getviews-pipeline-batch \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --update-env-vars "SERVICE_ROLE=batch"
}

# Post-deploy gate (audit 2026-06-10 H-3): a revision that boots broken
# (missing env var, import error) used to deploy "green" and serve 500s
# until someone noticed. Probe /health on the new revision; on failure,
# route 100% traffic back to the previous revision and exit non-zero.
verify_or_rollback() {
  local service="$1"
  local url
  url=$(gcloud run services describe "$service" \
    --project "$PROJECT_ID" --region "$REGION" \
    --format="value(status.url)" 2>/dev/null || true)
  if [[ -z "$url" ]]; then
    echo "✗ Could not resolve URL for $service — skipping health gate" >&2
    return 1
  fi
  echo "Health-checking $service at $url/health ..."
  for _ in $(seq 1 30); do
    if curl -sf --max-time 5 "$url/health" >/dev/null 2>&1; then
      echo "✓ $service healthy"
      return 0
    fi
    sleep 2
  done
  echo "✗ $service failed /health after 60s — rolling back to previous revision" >&2
  local prev
  prev=$(gcloud run revisions list --service "$service" \
    --project "$PROJECT_ID" --region "$REGION" \
    --format="value(metadata.name)" --sort-by="~metadata.creationTimestamp" \
    --limit 2 | tail -n 1)
  if [[ -n "$prev" ]]; then
    gcloud run services update-traffic "$service" \
      --project "$PROJECT_ID" --region "$REGION" \
      --to-revisions "$prev=100"
    echo "Traffic routed back to $prev. Investigate the failed revision, then redeploy." >&2
  else
    echo "No previous revision found — manual intervention required." >&2
  fi
  return 1
}

case "$TARGET" in
  user)  deploy_user;  verify_or_rollback getviews-pipeline-user ;;
  batch) deploy_batch; verify_or_rollback getviews-pipeline-batch ;;
  both)
    deploy_user;  verify_or_rollback getviews-pipeline-user
    deploy_batch; verify_or_rollback getviews-pipeline-batch
    ;;
esac

USER_URL=""
BATCH_URL=""
if [[ "$TARGET" == "user" || "$TARGET" == "both" ]]; then
  USER_URL=$(gcloud run services describe getviews-pipeline-user \
    --project "$PROJECT_ID" \
    --region "$REGION" --format="value(status.url)" 2>/dev/null || true)
fi
if [[ "$TARGET" == "batch" || "$TARGET" == "both" ]]; then
  BATCH_URL=$(gcloud run services describe getviews-pipeline-batch \
    --project "$PROJECT_ID" \
    --region "$REGION" --format="value(status.url)" 2>/dev/null || true)
fi

echo ""
[[ -n "$USER_URL"  ]] && echo "User service URL:  $USER_URL"
[[ -n "$BATCH_URL" ]] && echo "Batch service URL: $BATCH_URL"
echo ""
if [[ -n "$USER_URL" && -n "$BATCH_URL" ]]; then
  echo "Split deploy — register daily scripts + scene intelligence when cron uses the USER URL:"
  echo "  Supabase vault \`cloud_run_api_url\` may stay as the user URL (same as Vercel VITE_CLOUD_RUN_API_URL)."
  echo "  On getviews-pipeline-user, set (same BATCH_SECRET as batch, no trailing slash on batch URL):"
  echo "    gcloud run services update getviews-pipeline-user --region $REGION --project $PROJECT_ID \\"
  echo "      --update-env-vars BATCH_SERVICE_BASE_URL=$BATCH_URL,BATCH_SECRET=<SAME_AS_BATCH_SERVICE>"
  echo ""
fi
echo "Set env vars per service via (USE --update-env-vars, NOT --set-env-vars):"
echo "  gcloud run services update getviews-pipeline-user  --project $PROJECT_ID --region $REGION --update-env-vars KEY=VALUE"
echo "  gcloud run services update getviews-pipeline-batch --project $PROJECT_ID --region $REGION --update-env-vars KEY=VALUE"
echo ""
echo "  ``--set-env-vars`` REPLACES the entire env block — using it"
echo "  will wipe every variable not in the comma list and break JWT"
echo "  verification (jwks_url_unset 500). Always use --update-env-vars."
echo ""
echo "Required env vars (both services):"
echo "  GEMINI_API_KEY, ENSEMBLE_DATA_API_KEY,"
echo "  SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET"
echo ""
echo "Strongly recommended in production (cost/quota guards):"
echo "  RESIDENTIAL_PROXY_URL          — required for TikTok CDN downloads"
echo "                                   (Cloud Run datacenter IPs are blocked)"
echo "  ED_BATCH_DAILY_REQUEST_MAX     — per-day EnsembleData ceiling (0 = unlimited)"
echo "  ED_BATCH_BUDGET_ENFORCE        — true to enforce the cap (default: false / log-only)"
echo "  CLASSIFIER_GEMINI_DAILY_MAX    — per-day Tier-3 intent classifier cap (0 = unlimited)"
echo ""
echo "Batch-only env vars (getviews-pipeline-batch):"
echo "  SUPABASE_SERVICE_ROLE_KEY  — required for batch ingest DB writes"
echo "  BATCH_SECRET               — shared secret for POST /batch/ingest (recommended)"
echo "  BATCH_VIDEOS_PER_NICHE     — max videos analyzed per niche (default: 30)"
echo "  BATCH_RECENCY_DAYS         — post recency window in days (default: 30)"
echo "  BATCH_CONCURRENCY          — parallel niches per batch wave (default: 4)"
echo ""
echo "User-only (getviews-pipeline-user) when vault/cron use the *user* Cloud Run URL:"
echo "  BATCH_SERVICE_BASE_URL   — getviews-pipeline-batch status.url (no trailing slash);"
echo "    enables POST /batch/morning-ritual + /batch/scene-intelligence to forward to batch"
echo "  BATCH_SECRET            — same string as on batch; required for those forward routes"
echo ""
echo "Thumbnail backfill: POST <batch-service-url>/batch/backfill-thumbnails?ed_fallback=true"
echo "  (R2 frame0 copy → CDN mirror → EnsembleData fresh cover; &limit=N caps rows; needs ED + proxy env)"
echo ""
echo "R2 frame + video storage env vars (both services):"
echo "  R2_ACCOUNT_ID              — Cloudflare account ID"
echo "  R2_ACCESS_KEY_ID           — R2 API token access key (Object Read & Write)"
echo "  R2_SECRET_ACCESS_KEY       — R2 API token secret key"
echo "  R2_BUCKET_NAME             — R2 bucket name (default: getviews-frames)"
echo "  R2_PUBLIC_URL              — Public URL prefix for frames (e.g. https://media.getviews.vn)"
echo "  R2_VIDEO_PUBLIC_URL        — Public URL prefix for videos (defaults to R2_PUBLIC_URL)"
echo "                               Videos stored at: videos/{video_id}.mp4"
echo "                               Frames stored at: frames/{video_id}/{i}.png"
echo ""
echo "Cloud Scheduler jobs must point to the BATCH service URL:"
[[ -n "$BATCH_URL" ]] && SCHED_URL="$BATCH_URL" || SCHED_URL='$BATCH_SERVICE_URL'
echo ""
echo "  gcloud scheduler jobs create http getviews-corpus-ingest \\"
echo "    --location $REGION \\"
echo "    --schedule '0 2 * * *' \\"
echo "    --uri \"$SCHED_URL/batch/ingest\" \\"
echo "    --message-body '{}' \\"
echo "    --headers 'X-Batch-Secret=<YOUR_BATCH_SECRET>,Content-Type=application/json' \\"
echo "    --http-method POST \\"
echo "    --time-zone 'Asia/Ho_Chi_Minh' \\"
echo "    --attempt-deadline 30m"
echo ""
echo "  gcloud scheduler jobs create http getviews-morning-ritual \\"
echo "    --location $REGION \\"
echo "    --schedule '0 22 * * *' \\"
echo "    --uri \"$SCHED_URL/batch/morning-ritual\" \\"
echo "    --message-body '{}' \\"
echo "    --headers 'X-Batch-Secret=<YOUR_BATCH_SECRET>,Content-Type=application/json' \\"
echo "    --http-method POST \\"
echo "    --time-zone 'Asia/Ho_Chi_Minh' \\"
echo "    --attempt-deadline 25m"
echo ""
echo "  gcloud scheduler jobs create http getviews-scene-intelligence \\"
echo "    --location $REGION \\"
echo "    --schedule '30 3 * * *' \\"
echo "    --uri \"$SCHED_URL/batch/scene-intelligence\" \\"
echo "    --message-body '{}' \\"
echo "    --headers 'X-Batch-Secret=<YOUR_BATCH_SECRET>,Content-Type=application/json' \\"
echo "    --http-method POST \\"
echo "    --time-zone 'Asia/Ho_Chi_Minh' \\"
echo "    --attempt-deadline 45m"
echo ""
echo "  # R2 Janitor — weekly orphan cleanup (run dry_run=true first to sanity-check counts)"
echo "  gcloud scheduler jobs create http getviews-r2-janitor \\"
echo "    --location $REGION \\"
echo "    --schedule '0 18 * * 0' \\"
echo "    --uri \"$SCHED_URL/batch/r2-janitor?dry_run=false\" \\"
echo "    --message-body '{}' \\"
echo "    --headers 'X-Batch-Secret=<YOUR_BATCH_SECRET>,Content-Type=application/json' \\"
echo "    --http-method POST \\"
echo "    --time-zone 'UTC' \\"
echo "    --attempt-deadline 10m"
echo "  # Dry-run first: curl -s -X POST '$BATCH_URL/batch/r2-janitor?dry_run=true' \\"
echo "  #   -H 'X-Batch-Secret: <YOUR_BATCH_SECRET>' | jq .per_prefix"
echo ""
echo "Split deploy only: getviews-pipeline-user + getviews-pipeline-batch."
echo "The legacy single service name getviews-pipeline is retired — do not recreate it."
