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
#   SKIP_BUILD=1 ./deploy.sh ...  # reuse previous image
#
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
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

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "Building image $IMAGE..."
  gcloud builds submit --tag "$IMAGE" "$SCRIPT_DIR"
else
  echo "SKIP_BUILD=1 — reusing existing image $IMAGE"
fi

deploy_user() {
  # User-facing pod: needs 1 warm instance for snappy first-token SSE.
  # 300s timeout is plenty for the longest video analysis (Gemini caps
  # at ~120s end-to-end). Smaller memory than batch since one request
  # streams one video, not a corpus wave.
  echo ""
  echo "Deploying getviews-pipeline-user..."
  gcloud run deploy getviews-pipeline-user \
    --image "$IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 20 \
    --min-instances 1 \
    --max-instances 5 \
    --set-env-vars "SERVICE_ROLE=user"
}

deploy_batch() {
  # Batch pod: cold-starts are fine (Cloud Scheduler tolerates startup
  # latency). 4Gi to fit parallel TikTok MP4 downloads + Gemini fan-out.
  # 3600s timeout because all-niche ingest can run 10–30+ minutes.
  echo ""
  echo "Deploying getviews-pipeline-batch..."
  gcloud run deploy getviews-pipeline-batch \
    --image "$IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600 \
    --concurrency 5 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "SERVICE_ROLE=batch"
}

case "$TARGET" in
  user)  deploy_user ;;
  batch) deploy_batch ;;
  both)  deploy_user; deploy_batch ;;
esac

USER_URL=""
BATCH_URL=""
if [[ "$TARGET" == "user" || "$TARGET" == "both" ]]; then
  USER_URL=$(gcloud run services describe getviews-pipeline-user \
    --region "$REGION" --format="value(status.url)" 2>/dev/null || true)
fi
if [[ "$TARGET" == "batch" || "$TARGET" == "both" ]]; then
  BATCH_URL=$(gcloud run services describe getviews-pipeline-batch \
    --region "$REGION" --format="value(status.url)" 2>/dev/null || true)
fi

echo ""
[[ -n "$USER_URL"  ]] && echo "User service URL:  $USER_URL"
[[ -n "$BATCH_URL" ]] && echo "Batch service URL: $BATCH_URL"
echo ""
echo "Set env vars per service via:"
echo "  gcloud run services update getviews-pipeline-user  --region $REGION --set-env-vars KEY=VALUE"
echo "  gcloud run services update getviews-pipeline-batch --region $REGION --set-env-vars KEY=VALUE"
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
echo "  BATCH_VIDEOS_PER_NICHE     — max videos analyzed per niche (default: 10)"
echo "  BATCH_RECENCY_DAYS         — post recency window in days (default: 30)"
echo "  BATCH_CONCURRENCY          — parallel niches per batch wave (default: 4)"
echo ""
echo "R2 frame + video storage env vars (both services):"
echo "  R2_ACCOUNT_ID              — Cloudflare account ID"
echo "  R2_ACCESS_KEY_ID           — R2 API token access key (Object Read & Write)"
echo "  R2_SECRET_ACCESS_KEY       — R2 API token secret key"
echo "  R2_BUCKET_NAME             — R2 bucket name (default: getviews-media)"
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
echo "Migration note: the legacy single 'getviews-pipeline' service can be"
echo "deleted after Vercel + Cloud Scheduler are pointed at the new URLs:"
echo "  gcloud run services delete getviews-pipeline --region $REGION"
