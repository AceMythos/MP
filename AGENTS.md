## Project Context

This repository is for the **AI-Based Identity Anomaly Detection System** major project.

Before starting implementation or architecture work, read:

1. `CHECKPOINT.md`
2. `AI_IDENTITY_ANOMALY_PROJECT_NOTES.md`
3. `readme.md`

Current agreed direction:

- Build locally first.
- Use CSV upload as the first data source.
- Add synthetic UEBA data generation second.
- Add live Linux/Windows log ingestion later.
- Support identity and network-style UEBA fields.
- Build an enterprise SOC-style dashboard with strong UI/UX.
- Alert admins in v1; do not auto-block users.
- Include basic local admin login in v1, but do not add SSO/LDAP/MFA/RBAC yet.

Recommended v1 stack:

- Backend: FastAPI
- ML/data: pandas, scikit-learn
- DB: SQLite first, PostgreSQL later
- Frontend: React + Vite
- Styling: Tailwind CSS
- Charts: Recharts or ECharts

Recommended first milestone:

`CSV upload -> normalized events -> feature engineering -> rules + Isolation Forest -> risk scoring -> admin dashboard`

## Graphify

If `graphify-out/GRAPH_REPORT.md` exists, read it before answering architecture or codebase questions.

If `graphify-out/wiki/index.md` exists, prefer navigating the wiki instead of reading raw files.

After modifying code files, run:

```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

