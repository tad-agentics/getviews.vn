# Live-site quick-action audit

Playwright suite that drives the 6 quick-action cards on the chat screen against a live deployment and writes a per-intent audit.

## One-time setup

```bash
# install playwright deps (already in devDependencies)
npm i --legacy-peer-deps

# download the browser binary
npx playwright install chromium

# create the auth state — opens a real browser, you log in with Facebook/Google,
# the test detects /app and writes .auth/user.json.
npx playwright test auth.setup.ts --headed --project=setup
```

The session persists in `.auth/user.json` (gitignored). Re-run the setup step whenever it expires.

## Run the audit

```bash
# against production (default)
npx playwright test --project=quick-actions

# against a preview
GV_BASE_URL=https://preview-xxxx.vercel.app npx playwright test --project=quick-actions

# headed, slow, for debugging
npx playwright test --project=quick-actions --headed --workers=1
```

## Outputs

- `playwright-report/index.html` — HTML report with traces/videos on failure
- `playwright-report/results.json` — raw Playwright JSON
- `artifacts/qa-reports/quick-actions-live-YYYY-MM-DD.json` — per-card audit: intent, credit delta, latency, response excerpt, content checks

## Editing inputs

All test inputs (TikTok URL, handle, niches, topic, product) live at the top of `tests/quick-actions.spec.ts` in the `INPUTS` object.
