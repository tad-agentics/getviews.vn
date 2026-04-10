#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
SERVICE_NAME="getviews-pipeline"
REGION="asia-southeast1"  # Singapore — lowest latency to Vietnam

echo "Building image..."
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" .

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
  --min-instances 0 \
  --max-instances 5

echo ""
echo "Set env vars in Cloud Run console or via:"
echo "  gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars KEY=VALUE"
echo ""
echo "Required env vars:"
echo "  ENSEMBLE_DATA_API_KEY, GEMINI_API_KEY, SUPABASE_URL,"
echo "  SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET"
