# CI — Cloud Run image build

Production image: `gcr.io/<GCP_PROJECT_ID>/getviews-pipeline`

## Flow

| Step | Where | Command |
|------|--------|---------|
| **Build** | GitHub Actions (`cloud-run-build.yml`) on push to `main` (path-filtered) | `gcloud builds submit` |
| **Deploy** | Local or manual | `SKIP_BUILD=1 ./cloud-run/deploy.sh batch` (or `user` / `both`) |

Do **not** run full `deploy.sh` from laptop for every code change — let CI build; deploy only rolls out the image.

## One-time GitHub setup

This GCP project blocks service account JSON keys (`iam.disableServiceAccountKeyCreation`).
Use **Workload Identity Federation (WIF)** — the workflow authenticates via OIDC only.

### WIF setup (CLI)

```bash
export GCP_PROJECT_ID="project-ddfb2960-ee81-4c98-b4f"   # your project
export PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
export SA_NAME="github-cloud-run-build"
export SA_EMAIL="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
export REPO="tad-agentics/getviews.vn"                   # owner/repo

gcloud config set project "$GCP_PROJECT_ID"

# SA + Cloud Build roles (skip create if SA exists)
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="GitHub Actions Cloud Run build" 2>/dev/null || true
for role in roles/cloudbuild.builds.editor roles/storage.admin \
  roles/iam.serviceAccountUser roles/cloudbuild.builds.viewer roles/logging.viewer; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" --role="$role" --quiet
done

# Allow GitHub SA to act as the project's default Cloud Build runtime SA
gcloud iam service-accounts add-iam-policy-binding \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --project="$GCP_PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# WIF pool + GitHub OIDC provider
gcloud iam workload-identity-pools create github \
  --location=global --display-name="GitHub Actions Pool" 2>/dev/null || true
gcloud iam workload-identity-pools providers create-oidc github \
  --location=global --workload-identity-pool=github \
  --display-name="GitHub Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository=='${REPO}'"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${REPO}"

export WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github"

# GitHub secrets (requires `brew install gh` + `gh auth login`)
gh secret set GCP_PROJECT_ID --repo "$REPO" --body "$GCP_PROJECT_ID"
gh secret set GCP_WIF_PROVIDER --repo "$REPO" --body "$WIF_PROVIDER"
gh secret set GCP_WIF_SERVICE_ACCOUNT --repo "$REPO" --body "$SA_EMAIL"
gh secret list --repo "$REPO"
```

### Option A — Service account key (only if org policy allows)

1. Create SA e.g. `github-cloud-run-build@<project>.iam.gserviceaccount.com`
2. Roles (project):
   - `roles/cloudbuild.builds.editor`
   - `roles/storage.admin` (upload build context to `gs://<project>_cloudbuild`)
3. Create JSON key → GitHub repo **Secrets**:
   - `GCP_SA_KEY` — full JSON
   - `GCP_PROJECT_ID` — e.g. `project-ddfb2960-ee81-4c98-b4f`

> **Blocked on GetViews production project** — use WIF above instead.

### Option B — Workload Identity Federation (recommended)

Secrets (set via `gh secret set`):

- `GCP_WIF_PROVIDER` — `projects/…/locations/global/workloadIdentityPools/…/providers/…`
- `GCP_WIF_SERVICE_ACCOUNT` — `github-cloud-run-build@….iam.gserviceaccount.com`
- `GCP_PROJECT_ID`

See [Google: GitHub Actions WIF](https://github.com/google-github-actions/auth#workload-identity-federation).

## Local deploy after CI

```bash
export GCP_PROJECT_ID=your-project   # or gcloud config set project
SKIP_BUILD=1 ./cloud-run/deploy.sh batch   # or user | both
```

## Context size

Build context is **repo root** (for 3 junction migration SQL files). `.gcloudignore` / `.dockerignore` exclude `cloud-run/.venv`, `src/`, `artifacts/`, tests, etc. — upload should stay ~15–25 MB, not ~160 MB.

## Manual build (no CI)

```bash
./cloud-run/deploy.sh batch   # build + deploy
```
