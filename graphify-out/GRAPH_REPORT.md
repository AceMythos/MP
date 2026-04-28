# Graph Report - .  (2026-04-28)

## Corpus Check
- 14 files · ~72,064 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 66 nodes · 79 edges · 13 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]

## God Nodes (most connected - your core abstractions)
1. `_upload_csv()` - 9 edges
2. `Base` - 5 edges
3. `normalize_row()` - 4 edges
4. `Settings` - 3 edges
5. `_create_combined_risk_alerts()` - 3 edges
6. `init_database()` - 3 edges
7. `get_settings()` - 2 edges
8. `_parse_int()` - 2 edges
9. `_parse_float()` - 2 edges
10. `_parse_datetime()` - 2 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities

### Community 0 - "Community 0"
Cohesion: 0.33
Nodes (9): test_csv_ingestion_and_event_listing(), test_csv_ingestion_marks_job_failed_for_invalid_port(), test_csv_ingestion_rejects_missing_required_columns(), test_dashboard_overview_returns_security_summary_counts(), test_isolation_forest_detection_is_idempotent_for_alert_creation(), test_isolation_forest_detection_scores_events_and_creates_ml_alerts(), test_rule_engine_flags_new_ip_for_established_account(), test_user_risk_summary_ranks_accounts_by_alert_score() (+1 more)

### Community 1 - "Community 1"
Cohesion: 0.39
Nodes (8): BaseModel, AlertResponse, DashboardOverview, EventResponse, HealthResponse, IngestionResponse, MlDetectionResponse, UserRiskSummary

### Community 2 - "Community 2"
Cohesion: 0.25
Nodes (0): 

### Community 3 - "Community 3"
Cohesion: 0.43
Nodes (4): normalize_row(), _parse_datetime(), _parse_float(), _parse_int()

### Community 4 - "Community 4"
Cohesion: 0.53
Nodes (5): DeclarativeBase, Alert, Base, Event, IngestionJob

### Community 5 - "Community 5"
Cohesion: 0.47
Nodes (3): _ensure_sqlite_event_ml_columns(), _ensure_sqlite_ingestion_error_message_column(), init_database()

### Community 6 - "Community 6"
Cohesion: 0.5
Nodes (2): onUpload(), refreshData()

### Community 7 - "Community 7"
Cohesion: 0.67
Nodes (3): BaseSettings, get_settings(), Settings

### Community 8 - "Community 8"
Cohesion: 0.83
Nodes (3): _create_combined_risk_alerts(), run_isolation_forest_detection(), _score_to_severity()

### Community 9 - "Community 9"
Cohesion: 0.67
Nodes (0): 

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **Thin community `Community 10`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Not enough signal to generate questions. This usually means the corpus has no AMBIGUOUS edges, no bridge nodes, no INFERRED relationships, and all communities are tightly cohesive. Add more files or run with --mode deep to extract richer edges._