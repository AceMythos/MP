# Checkpoint - AI-Based Identity Anomaly Detection System

Date: 2026-04-24

## What Happened So Far

We reviewed the project presentation PDF from Downloads:

`/home/igris/Downloads/MAJOR PROJECT PPT_20260416_135448_0000.pdf`

The deck proposed an AI-based UEBA identity anomaly detection system using authentication/authorization logs, anomaly detection models, risk scoring, and a dashboard.

We then used the `grill-me` skill to pressure-test the project before building.

## Main Review Outcome

The original idea is good, but too broad if built directly.

The first version should be a serious local baseline, not a fake enterprise system and not an over-scoped 4-model platform.

Current verdict: `borderline`, but viable if built in stages.

## User Decisions

- Build locally first.
- Use CSV upload first.
- Add synthetic UEBA data second.
- Add live Linux/Windows logs later.
- Support both identity and network-style UEBA.
- Dashboard should look like an enterprise SOC/security command center.
- UI should be smooth, informative, visually strong, and easy to navigate.
- Start with admin alerts only.
- Do not auto-block users in v1.
- The system does not need to follow the presentation exactly.
- The user is a beginner and wants guided implementation.

## V1 Product Shape

The v1 system should include:

- Basic local admin login
- CSV upload
- CSV field mapping and normalization
- Event storage
- Feature engineering
- Rule-based anomaly signals
- Isolation Forest anomaly detection
- Risk scoring from 0 to 100
- Severity levels: Low, Medium, High, Critical
- Explainable reason codes
- Alert dashboard
- User risk view
- Anomaly/event table
- Basic admin audit log

## V1 Non-Goals

Do not build these first:

- Automatic blocking
- SSO
- LDAP
- Okta
- MFA
- Full RBAC
- Full SIEM integration
- Production deployment
- Four-model ML ensemble
- Cloud deployment

## Data Model Direction

Expected UEBA/network fields may include:

- account
- group
- ip
- url
- port
- vlan
- switch_ip
- time

Normalize incoming records into an internal event schema similar to:

```txt
event_id
timestamp
account
group
source_ip
destination_ip
url
port
vlan
switch_ip
device
country
action
status
resource
raw_source
```

## Detection Direction

Use hybrid detection:

- Rules for explainable security signals.
- Isolation Forest for ML anomaly detection.
- Combined risk score for final severity.

Initial detection ideas:

- New device for user
- New source IP or country
- Impossible travel / rapid location change
- Failed login burst followed by success
- Login outside normal hours
- Unusual URL/resource
- Unusual port/VLAN for account or group
- Group/privilege change if available
- User behavior different from own history
- User behavior different from group/global baseline

## Metrics

Prefer these over plain accuracy:

- False positive rate per 1,000 events
- Precision at top alerts
- Recall on injected/synthetic attacks
- Mean time to detection
- Alert explainability rate

## Recommended Next Step

Start implementation with:

`CSV upload -> normalized events -> feature engineering -> rules + Isolation Forest -> risk scoring -> admin dashboard`

Use:

- FastAPI backend
- SQLite database first
- pandas + scikit-learn
- React + Vite frontend
- Tailwind CSS
- Recharts or ECharts

Keep the architecture clean enough to upgrade later to PostgreSQL, live logs, richer models, and enterprise auth.

---

## Current Build Status

### Stage 1 - Backend Skeleton

Completed locally.

Implemented:

- FastAPI backend skeleton
- `/health` endpoint
- config loading
- SQLite engine/session setup
- local `.venv`
- passing Stage 1 test

Important files:

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/db.py`
- `backend/tests/test_health.py`
- `backend/requirements.txt`

### Stage 2 - CSV Ingestion

Completed and pushed on branch:

`stage-1-backend-skeleton`

Dataset source confirmed:

- `/home/igris/Downloads/archive.zip`

Archive contents:

- `train_data.csv`
- `A_test_data.csv`

Confirmed dataset fields:

```txt
id
account
group
IP
url
port
vlan
switchIP
time
ret   # training file only
```

Stage 2 work completed:

- SQLAlchemy models for:
  - `IngestionJob`
  - `Event`
- persisted `Alert` model for rule-based findings
- CSV parsing and normalization logic in `backend/app/ingestion.py`
- field mapping from Kaggle schema to internal event schema
- CSV upload endpoint:
  - `POST /ingestions/csv`
- event listing endpoint:
  - `GET /events`
- alert listing endpoint:
  - `GET /alerts`
- user risk summary endpoint:
  - `GET /risk/users`
- dashboard summary endpoint:
  - `GET /dashboard/overview`
- rule engine for:
  - outside-standard-hours activity
  - sensitive/internal URL targets
  - new source IP for established accounts
  - unusual port for account
  - unusual VLAN for account
- schema models for API responses
- backend tests covering ingestion, alerts, user summaries, and dashboard overview

Stage 2 files touched:

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/ingestion.py`
- `backend/app/db.py`
- `backend/app/main.py`
- `backend/tests/test_health.py`
- `backend/requirements.txt`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/graph.json`

### Git Status

Remote branch pushed:

`origin/stage-1-backend-skeleton`

Pushed commits:

- `f4d6d97` `feat: bootstrap backend ingestion and alerts`
- `dff1712` `feat: add user risk summaries`

Current local work to be pushed next:

- dashboard overview endpoint
- updated tests
- refreshed graphify output

### Current Backend State

Verified locally:

- `.venv/bin/pytest backend` -> `5 passed`
- SQLite-backed ingestion works through direct endpoint invocation in tests
- `GET /health`
- `POST /ingestions/csv`
- `GET /events`
- `GET /alerts`
- `GET /risk/users`
- `GET /dashboard/overview`

### Next Recommended Step

Start Stage 4:

`feature engineering -> Isolation Forest baseline -> ML anomaly score -> combine with rule score`

## Resume Instructions

When resuming:

1. Activate local venv:

```bash
source .venv/bin/activate
```

2. Run tests:

```bash
.venv/bin/pytest backend
```

3. If needed, install any missing dependency from:

```bash
backend/requirements.txt
```

4. Verify current endpoints:

```bash
GET /health
POST /ingestions/csv
GET /events
GET /alerts
GET /risk/users
GET /dashboard/overview
```

5. Push the current local dashboard overview commit if it has not been pushed yet.

6. Continue with Stage 4 ML baseline work.

- `POST /ingestions/csv`
- `GET /events`

5. Test with the real dataset from:

`/home/igris/Downloads/archive.zip`

6. After verification:

- commit Stage 2
- push branch to GitHub

## Immediate Next Goal

Finish verifying Stage 2 against the real dataset archive, then commit and push before starting Stage 3.
