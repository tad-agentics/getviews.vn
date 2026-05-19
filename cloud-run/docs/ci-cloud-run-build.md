# CI — Cloud Run image build

Production image: `gcr.io/<GCP_PROJECT_ID>/getviews-pipeline`

## Flow

| Step | Where | Command |
|------|--------|---------|
| **Build** | GitHub Actions (`cloud-run-build.yml`) on push to `main` (path-filtered) | `gcloud builds submit` |
| **Deploy** | Local or manual | `SKIP_BUILD=1 ./cloud-run/deploy.sh batch` (or `user` / `both`) |

Do **not** run full `deploy.sh` from laptop for every code change — let CI build; deploy only rolls out the image.

## One-time GitHub setup

### Option A — Service account key (fastest)

1. Create SA e.g. `github-cloud-run-build@<project>.iam.gserviceaccount.com`
2. Roles (project):
   - `roles/cloudbuild.builds.editor`
   - `roles/storage.admin` (upload build context to `gs://<project>_cloudbuild`)
   - `roles/artifactregistry.writer` or legacy GCR: ensure Cloud Build default SA can push (`roles/storage.admin` on GCR bucket is often already wired for Cloud Build)
3. Create JSON key → GitHub repo **Secrets**:
   - `GCP_SA_KEY` — full JSON
   - `GCP_PROJECT_ID` — e.g. `project-ddfb2960-ee81-4c98-b4f`

### Option B — Workload Identity Federation (recommended)

Follow [Google: GitHub Actions WIF](https://github.com/google-github-actions/auth#workload-identity-federation).

Secrets:

- `GCP_WIF_PROVIDER` — `projects/…/locations/global/workloadIdentityPools/…/providers/…`
- `GCP_WIF_SERVICE_ACCOUNT` — `github-cloud-run-build@….iam.gserviceaccount.com`
- `GCP_PROJECT_ID`

Update `.github/workflows/cloud-run-build.yml` `auth` step to use WIF fields instead of `GCP_SA_KEY` when ready.

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
