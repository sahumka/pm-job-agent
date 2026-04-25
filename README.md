# PM Job Search Copilot

Local-first multi-user job search system for discovery, scoring, tracking, automation, and assisted resume preparation.

## Key Features
- Multi-user profile onboarding (`shiven_analytics`, `tanya_product`, `shreya_finance`)
- Per-profile source isolation (`config/users/<profile>/target_companies.csv`, `linkedin_jobs.csv`, `manual_jobs.csv`)
- Job collection from Greenhouse, Lever, Ashby, generic careers pages, plus manual/LinkedIn CSV import
- Rule-based scoring with no paid API required
- SQLite storage with dedupe and run logging
- Streamlit dashboard with pipeline tracking, URL validation tools, and run history/retry controls
- Hourly automation runner + GitHub Actions workflow
- Base resume intake per user (PDF/DOCX/TXT/MD -> canonical Markdown)

## Quick Start (PowerShell)
```powershell
cd "C:\Users\shive\Python Projects\pm-job-agent"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "from src.db import init_db; init_db('data/jobs.db'); print('DB initialized')"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8513
```

One-command launcher:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

## Packaging & CLI
Editable install:
```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

CLI commands:
- `pmcopilot-run-daily`
- `pmcopilot-run-hourly`
- `pmcopilot-validate-targets`
- `pmcopilot-dashboard`
- `pmcopilot-email-digest`
- `pmcopilot-healthcheck`
- `pmcopilot-retry-latest-failed`

## Important Paths
- Targets: `config/target_companies.csv`
- Manual imports: `config/manual_jobs.csv`
- LinkedIn imports: `config/linkedin_jobs.csv`
- Database: `data/jobs.db`
- Logs: `logs/`
- Outputs: `outputs/`

## Automation
Hourly run:
```powershell
python -m src.run_hourly --db-path data/jobs.db --summary-path outputs/hourly_summary.json
```

Selected profiles:
```powershell
python -m src.run_hourly --profiles shiven_analytics,tanya_product --db-path data/jobs.db
```

PowerShell helper:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_hourly.ps1
```

## Operations (Backup / Health / Release)
Healthcheck:
```powershell
python -m src.healthcheck --db-path data/jobs.db --output-json outputs/healthcheck.json
```
or:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\healthcheck.ps1
```

Backup data/config:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup_data.ps1
```

Create a shareable release zip:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_release.ps1
```

GitHub Actions:
- `.github/workflows/hourly_job_collection.yml` (every 2 hours + manual)
- `.github/workflows/test_crawl_25_companies.yml` (manual test run with 25 companies)
- `.github/workflows/ci.yml` (ruff + compile + tests)
- `.github/workflows/retry_latest_failed_per_profile.yml` (manual on-demand retry mode)

Each workflow now writes an **Ops Summary** in the GitHub Actions run summary panel (profiles run, inserted, duplicates, failures, retry selection).

Required repository secrets for digest email:
- `EMAIL_FROM`
- `EMAIL_PASSWORD`
- `EMAIL_TO`

Optional SMTP overrides:
- `SMTP_HOST` (default `smtp.gmail.com`)
- `SMTP_PORT` (default `465`)

Hourly workflow notifications:
- Sends email when crawl starts
- Sends a 1-hour in-progress email (only if still running)
- Sends final completion/failure email with summary metrics
- Auto-skips stale scheduled runs if queue delay exceeds 20 minutes
- Sends per-profile summary emails (new listings + high-quality listings) to each profile's `notification_email`

Profile email routing:
- Set `notification_email` in each `config/users/<profile>.yaml`
- Sender comes from `EMAIL_FROM` / `EMAIL_PASSWORD` secrets
- Example profiles:
  - `shiven_analytics -> shivenahuja94@gmail.com`
  - `tanya_product -> tanyagopal14@gmail.com`
  - `shreya_finance -> shreyaahuja1997@gmail.com`

Profile-isolated sources:
- Hourly runs use per-profile files by default:
  - `config/users/<profile_id>/target_companies.csv`
  - `config/users/<profile_id>/linkedin_jobs.csv`
  - `config/users/<profile_id>/manual_jobs.csv`
- If a profile file is missing, it is bootstrapped from shared defaults once.
- In Streamlit `Profile Setup`, use **Initialize/Refresh Profile Source Files** to create/update these files.

Profile crawl activation:
- A profile becomes crawl-active on first successful Profile Setup save.
- Production hourly crawl runs only profiles that are both configured and `crawl_active: true`.
- In Streamlit `Dashboard`, select a profile and use **Make Active / Make Inactive** to control whether that profile participates in scheduled crawls.

Manual test crawl workflow:
- `Test Crawl (25 Companies)` can be run on demand from Actions
- It builds `config/target_companies_test_25.csv` from the first 25 enabled companies
- Useful for fast validation before full hourly/daily crawls

Optional LLM/API secrets:
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`

Manual retry workflow (latest failed per profile):
- Open `Actions` -> `Retry Latest Failed Per Profile`
- Click `Run workflow`
- Optional inputs:
  - `profiles`: comma-separated profile ids to constrain retries
  - `run_types`: defaults to `hourly`
  - `timeout`: request timeout seconds

## URL Validation
Validate and classify target URLs:
```powershell
python -m src.validate_targets --input-csv config/target_companies.csv --output-dir outputs/url_validation --timeout 8 --max-workers 32
```

Dry run sample:
```powershell
python -m src.validate_targets --input-csv config/target_companies.csv --limit 200
```

PowerShell helper:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_targets.ps1
```

Outputs:
- `outputs/url_validation/validation_report.csv`
- `outputs/url_validation/valid_targets.csv`
- `outputs/url_validation/failed_targets.csv`
- `outputs/url_validation/summary.json`

Streamlit includes:
- Run validator from UI
- Apply `valid_targets.csv` to `config/target_companies.csv` (with backup)
- Apply only suggested/redirected fixes (with backup)

## Run History & Retry (UI)
`Run History` page provides:
- Run filters (profile/status/run type)
- CSV export
- Retry modes:
  - Retry all failed profiles
  - Retry latest failed run per profile

## Resume Intake
In `Profile Setup` -> `Resume Intake`:
- Upload `.pdf`, `.docx`, `.txt`, `.md`
- Saved to `data/resumes/<user_id>/base_resume.<ext>`
- Canonical text stored as `data/resumes/<user_id>/base_resume.md`

## Runtime Configuration (.env)
Copy `.env.example` and configure as needed:
- Email: `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_TO`, `SMTP_HOST`, `SMTP_PORT`
- Paths/logging: `DB_PATH`, `LOGS_DIR`, `LOG_JSON`
- Source guardrail:
  - `SOURCE_AUTO_DISABLE_EMPTY=true|false`
  - `SOURCE_AUTO_DISABLE_SCORE_MAX=5`

## Source Health Diagnostics
`run_daily` emits:
- `outputs/source_health.json`
- `outputs/source_health.csv`

This helps identify noisy/low-yield sources.

## Docker (Optional)
```powershell
docker compose up --build
```
Dashboard: `http://127.0.0.1:8513`

## Dev Tooling
- `pyproject.toml` (package metadata + entrypoints)
- `.pre-commit-config.yaml`
- `ruff` linting (via CI and optional pre-commit)

Install pre-commit:
```powershell
.\.venv\Scripts\python.exe -m pip install pre-commit
.\.venv\Scripts\pre-commit.exe install
```

## Tests
```powershell
python -m pytest -q
```
