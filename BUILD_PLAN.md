# Systematic Build Plan

Goal: build the AI-Based Identity Anomaly Detection System in small, verifiable stages inside this `MP` repo, with clean GitHub updates after each stable milestone.

## Working Method

- Work on a branch per stage or major slice.
- Keep each stage small enough to run and verify locally.
- Commit only after the stage works.
- Push to GitHub after each completed stage.
- Update `CHECKPOINT.md` when a major decision changes.
- Run graphify after code changes:

```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

## Stage 0 - Repo Foundation

Purpose: prepare the repo so future work is structured and easy to resume.

Tasks:

- [ ] Create backend and frontend folders.
- [ ] Add root project docs and development commands.
- [ ] Add `.gitignore` for Python, Node, SQLite, logs, and env files.
- [ ] Add `.env.example` with safe placeholder config.
- [ ] Commit and push the planning/checkpoint files.

Done when:

- [ ] A new Codex session in `MP` can read `AGENTS.md`, `CHECKPOINT.md`, and this file and know what to do.
- [ ] GitHub has the project docs and repo foundation.

## Stage 1 - Backend Skeleton

Purpose: create a local FastAPI backend that is alive, testable, and ready for data ingestion.

Tasks:

- [ ] Create FastAPI app structure.
- [ ] Add health endpoint: `GET /health`.
- [ ] Add config loading.
- [ ] Add SQLite database setup.
- [ ] Add basic test for health endpoint.

Done when:

- [ ] Backend starts locally.
- [ ] `GET /health` returns success.
- [ ] Backend tests pass.

## Stage 2 - Event Schema And CSV Ingestion

Purpose: upload UEBA CSV files and normalize records into an internal event schema.

Tasks:

- [ ] Define normalized event model.
- [ ] Add CSV upload endpoint.
- [ ] Add field mapping for known UEBA columns: account, group, ip, url, port, vlan, switch_ip, time.
- [ ] Store raw and normalized events.
- [ ] Add endpoint to list ingested events.

Done when:

- [ ] A sample CSV can be uploaded.
- [ ] Events are stored in SQLite.
- [ ] API can return normalized events.

## Stage 3 - Rule-Based Detection

Purpose: produce useful alerts before ML is added.

Tasks:

- [ ] Implement rule signals for missing/rare fields.
- [ ] Add rules for unusual time, new IP, unusual port/VLAN, suspicious URL/resource, and failed-then-success patterns where data exists.
- [ ] Generate reason codes for each alert.
- [ ] Add severity calculation: Low, Medium, High, Critical.
- [ ] Add alert listing endpoint.

Done when:

- [ ] Ingested events can produce explainable alerts.
- [ ] Each alert includes score, severity, and reason codes.

## Stage 4 - ML Baseline

Purpose: add the first anomaly model without overcomplicating the system.

Tasks:

- [ ] Create feature engineering pipeline.
- [ ] Encode categorical and numeric event features.
- [ ] Train Isolation Forest on ingested data.
- [ ] Generate ML anomaly score per event.
- [ ] Combine rule score and ML score into final risk score.

Done when:

- [ ] API can run detection on uploaded CSV data.
- [ ] Alerts include both rule reasons and ML anomaly score.
- [ ] Detection is repeatable on the same dataset.

## Stage 5 - Frontend Skeleton

Purpose: create the React app and basic navigation before building the full dashboard.

Tasks:

- [ ] Create React + Vite frontend.
- [ ] Add Tailwind CSS.
- [ ] Add dark enterprise SOC-style layout.
- [ ] Add routes for Login, Dashboard, Upload, Alerts, Events, Users.
- [ ] Connect frontend to backend health endpoint.

Done when:

- [ ] Frontend runs locally.
- [ ] Dashboard shell loads.
- [ ] Frontend can show backend health status.

## Stage 6 - Admin Login

Purpose: protect the dashboard with simple local admin authentication.

Tasks:

- [ ] Add local admin user model.
- [ ] Store password hash, not plain text.
- [ ] Add login endpoint.
- [ ] Add session or JWT handling.
- [ ] Protect dashboard routes.
- [ ] Add audit event for login.

Done when:

- [ ] User must log in before viewing dashboard.
- [ ] Invalid credentials are rejected.
- [ ] Login action appears in audit log.

## Stage 7 - SOC Dashboard

Purpose: make the product feel useful, impressive, and easy to navigate.

Tasks:

- [ ] Add CSV upload screen.
- [ ] Add dashboard summary cards: total events, alerts, high risk users, critical alerts.
- [ ] Add risk trend chart.
- [ ] Add severity distribution chart.
- [ ] Add recent alerts table.
- [ ] Add event explorer table with filtering.

Done when:

- [ ] User can upload CSV and see events/alerts in the UI.
- [ ] Dashboard is visually polished and informative.
- [ ] Main workflows are understandable without explanation text.

## Stage 8 - Synthetic Data Generator

Purpose: make demos reliable even without a Kaggle file.

Tasks:

- [ ] Add backend generator for normal identity/network events.
- [ ] Inject synthetic anomalies.
- [ ] Add UI action to generate demo data.
- [ ] Label generated anomalies for evaluation.
- [ ] Add basic metrics from generated data.

Done when:

- [ ] User can generate a demo dataset locally.
- [ ] Dashboard shows realistic alerts from synthetic events.
- [ ] Metrics can compare detected alerts against injected anomalies.

## Stage 9 - Evaluation And Hardening

Purpose: make the baseline defensible.

Tasks:

- [ ] Add precision-at-top-alerts calculation for labeled synthetic data.
- [ ] Add false positive rate per 1,000 events.
- [ ] Add explainability coverage metric.
- [ ] Add input validation and CSV error reporting.
- [ ] Add backend and frontend smoke tests.

Done when:

- [ ] The system can explain how well it performs on synthetic labeled data.
- [ ] Bad CSV files fail with useful errors.
- [ ] Tests pass locally.

## Stage 10 - Live Logs Later

Purpose: add live log ingestion only after the CSV pipeline is solid.

Tasks:

- [ ] Add Linux auth log tailing prototype.
- [ ] Map Linux auth events to normalized schema.
- [ ] Add Windows event log plan or prototype.
- [ ] Keep live logs behind a separate ingestion source.

Done when:

- [ ] Live logs can create normalized events without breaking CSV ingestion.
- [ ] Dashboard can distinguish CSV, synthetic, and live-log sources.

## First Action To Start Building

Start with **Stage 0**.

Recommended first commands/actions:

1. Create a branch such as `stage-0-foundation`.
2. Add repo foundation files.
3. Commit `AGENTS.md`, `CHECKPOINT.md`, `AI_IDENTITY_ANOMALY_PROJECT_NOTES.md`, and `BUILD_PLAN.md`.
4. Push the branch to GitHub.

