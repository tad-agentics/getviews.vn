# EnsembleData observability & SLO hooks

## Per-batch log line

Cloud Run logs include **`[ed-meter]`** at the end of:

- `run_batch_ingest` (`label=batch_ingest`)
- `run_reingest_video_items` (`label=reingest_videos`)

Fields: `batch_id`, `requests` (counts by endpoint key), `est_units`, `est_units_per_insert`, optional `theoretical_pool` (batch ingest only).

## Cloud Logging alerts (manual setup)

Suggested filters (adapt project id):

- Alert when `textPayload:"[ed-meter]"` AND `textPayload:"est_units_per_insert"` with regex for values **> 12** (tune after baseline).
- Alert when daily sum of `est_units` from log-based metrics exceeds `ED_DAILY_ALERT_THRESHOLD` (define after calibration).

## Theoretical budget on PRs

`pytest cloud-run/tests/test_ed_metering.py -q` prints stable expectations for default pool caps. When changing `BATCH_*` env defaults, update the test constants so reviewers see the projected ED HTTP delta.
