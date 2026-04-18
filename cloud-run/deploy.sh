#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
SERVICE_NAME="getviews-pipeline"
REGION="asia-southeast1"  # Singapore — lowest latency to Vietnam

echo "Building image..."
# Build using the cloud-run/ directory as context so the correct Dockerfile is used
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" "$SCRIPT_DIR"

echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 20 \
  --min-instances 1 \
  --max-instances 5

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format="value(status.url)")

echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "Set env vars in Cloud Run console or via:"
echo "  gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars KEY=VALUE"
echo ""
echo "Required env vars:"
echo "  ENSEMBLE_DATA_API_KEY, GEMINI_API_KEY, SUPABASE_URL,"
echo "  SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET"
echo ""
echo "Batch corpus ingest env vars (optional):"
echo "  SUPABASE_SERVICE_ROLE_KEY  — required for batch ingest DB writes"
echo "  BATCH_SECRET               — shared secret for POST /batch/ingest (recommended)"
echo "  BATCH_VIDEOS_PER_NICHE     — max videos analyzed per niche (default: 10)"
echo "  BATCH_RECENCY_DAYS         — post recency window in days (default: 30)"
echo "  BATCH_CONCURRENCY          — parallel niches per batch wave (default: 4)"
echo ""
echo "R2 frame + video storage env vars (optional — skip to leave frame_urls/video_url as ED CDN URLs):"
echo "  R2_ACCOUNT_ID              — Cloudflare account ID"
echo "  R2_ACCESS_KEY_ID           — R2 API token access key (Object Read & Write)"
echo "  R2_SECRET_ACCESS_KEY       — R2 API token secret key"
echo "  R2_BUCKET_NAME             — R2 bucket name (default: getviews-media)"
echo "  R2_PUBLIC_URL              — Public URL prefix for frames (e.g. https://media.getviews.vn)"
echo "  R2_VIDEO_PUBLIC_URL        — Public URL prefix for videos (defaults to R2_PUBLIC_URL)"
echo "                               Videos stored at: videos/{video_id}.mp4"
echo "                               Frames stored at: frames/{video_id}/{i}.png"
echo ""
echo "To set up Cloud Scheduler for nightly corpus ingest (02:00 ICT):"
echo "  gcloud scheduler jobs create http getviews-corpus-ingest \\"
echo "    --location $REGION \\"
echo "    --schedule '0 2 * * *' \\"
echo "    --uri \"$SERVICE_URL/batch/ingest\" \\"
echo "    --message-body '{}' \\"
echo "    --headers 'X-Batch-Secret=<YOUR_BATCH_SECRET>,Content-Type=application/json' \\"
echo "    --http-method POST \\"
echo "    --time-zone 'Asia/Ho_Chi_Minh' \\"
echo "    --attempt-deadline 25m"
echo ""
echo "To set up Cloud Scheduler for nightly morning ritual (22:00 ICT = before users wake):"
echo "  gcloud scheduler jobs create http getviews-morning-ritual \\"
echo "    --location $REGION \\"
echo "    --schedule '0 22 * * *' \\"
echo "    --uri \"$SERVICE_URL/batch/morning-ritual\" \\"
echo "    --message-body '{}' \\"
echo "    --headers 'X-Batch-Secret=<YOUR_BATCH_SECRET>,Content-Type=application/json' \\"
echo "    --http-method POST \\"
echo "    --time-zone 'Asia/Ho_Chi_Minh' \\"
echo "    --attempt-deadline 25m"
