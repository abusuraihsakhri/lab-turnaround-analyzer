# Lab Turnaround Analyzer

Laboratory turnaround-time (TAT) analysis from LIS CSV timestamps, with a standalone, browser-based dashboard and Python CLI/API. The browser version works entirely on-device, without a Python backend.

## Features

- Total and test-stratified TAT in elapsed minutes, with mean, P50, P90, P95 and maximum.
- Target breach counts and rates (TAT strictly greater than a configurable target).
- Upper IQR outlier flags per test (Q3 + 1.5 × IQR, applied only when at least four records exist).
- Export of annotated CSV and aggregate JSON; input validation with clear row-level errors.
- Existing lookup, agent audit, mock supervisory chat, simulation and enrichment interfaces remain available.

## Use in the browser

Open the published GitHub Pages application when Pages deployment is enabled, or open `web/index.html` directly in a modern browser. Choose a CSV file, set the TAT target in minutes, and select **Analyze CSV**. **Load example** runs the synthetic dataset without uploading a file. Exports are generated locally.

The browser requires no backend, account, network request, model provider, cookies or persistent browser storage. Data remain in the active page until the tab is closed or another dataset is analyzed. Downloaded files remain wherever you save them.

## CSV input

Required columns are `test`, `received_at` and `reported_at`. An optional `specimen_id` or other columns are preserved in annotated CSV output. Each timestamp must include a timezone offset or `Z`. Example:

```csv
test,received_at,reported_at,specimen_id
CBC,2026-10-01T08:00:00Z,2026-10-01T08:30:00Z,S-001
CBC,2026-10-01T08:00:00Z,2026-10-01T09:15:00Z,S-002
CRP,2026-10-01T10:00:00+02:00,2026-10-01T09:20:00Z,S-003
```

TAT is calculated as reported time minus received time after time-zone normalization. Negative durations, malformed timestamps, missing fields, empty datasets and invalid targets are rejected; rows are not silently dropped. Both implementations limit analyses to 20,000 records and 2,000,000 characters of CSV. Percentiles use linear interpolation at position `(n-1) × p`. Metrics are descriptive quality indicators, **not** clinical urgency classifications or patient-care decisions.

## Python CLI

Requires Python 3.10 or later.

```bash
python -m pip install -e ".[dev]"
python tat_analyzer.py analyze --input lis.csv --threshold-minutes 60 \
  --output tat-annotated.csv --report tat-summary.json
# Equivalent installed CLI:
lab-turnaround-analyzer analyze-tat --input lis.csv --threshold-minutes 60
```

The CSV and JSON outputs are optional. Without them, the summary is printed to standard output.

The legacy lookup commands are preserved:

```bash
python tat_analyzer.py single creatinine
python tat_analyzer.py batch --input sample.csv --output lookup-output.csv
lab-turnaround-analyzer audit --task-id TASK-001
lab-turnaround-analyzer verify-audit
```

## Optional FastAPI service

```bash
lab-turnaround-analyzer serve --host 127.0.0.1 --port 8000
```

`POST /api/tat/analyze` accepts JSON with `csv_text` and `threshold_minutes`, returning aggregate TAT statistics without raw records. Legacy `/api/audit`, `/api/chat`, `/api/audit/logs`, `/metrics` and `/health` routes are retained. The legacy agent thresholds are generic and must not be mistaken for TAT clinical limits.

## Security and privacy

The browser performs local CSV processing and makes no automatic data submissions. CSV exports neutralize leading spreadsheet formulas in user-provided fields. The Python/API service processes data server-side and is **not** an authenticated, HIPAA-compliant clinical information system. Use de-identified or appropriately authorized data and secure network controls for deployments. PHI pattern screening in the legacy agent interface is best-effort, not comprehensive de-identification. The HMAC audit chain is in-memory and does not provide durable, independently witnessed audit storage.

## Development and verification

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
node --check web/app.js
node --test web/app.test.js
python -m compileall -q agents cli.py tat_analyzer.py tat_metrics.py enrichment.py simulator.py
```

CI tests Python 3.10–3.13 and Node.js 22. GitHub Pages deploys only the static `web/index.html` and `web/app.js` assets from `master` when Pages is enabled and the deployment workflow succeeds. No Pyodide is required because the browser implementation is plain JavaScript.

## Technology and license

Python standard library, FastAPI/Pydantic for the optional service, and dependency-free browser JavaScript. Tested by CI on the specified runtimes; modern Chrome, Firefox, Safari and Edge are intended browser targets. MIT license; see [LICENSE](LICENSE).
