import json

from fastapi import Depends, FastAPI, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import check_database, get_db, init_database
from app.ingestion import create_rule_alerts, normalize_row, parse_csv_bytes
from app.models import Alert, Event, IngestionJob
from app.schemas import (
    AlertResponse,
    DashboardOverview,
    EventResponse,
    HealthResponse,
    IngestionResponse,
    UserRiskSummary,
)


settings = get_settings()
app = FastAPI(title=settings.app_name)
init_database()


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> dict[str, str]:
    database_ok = check_database()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "database": "ok" if database_ok else "down",
    }


@app.post("/ingestions/csv", response_model=IngestionResponse)
def ingest_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> IngestionResponse:
    payload = file.file.read()
    rows = parse_csv_bytes(payload)

    ingestion = IngestionJob(
        filename=file.filename or "upload.csv",
        source_kind="csv_upload",
        records_total=len(rows),
        status="completed",
    )
    db.add(ingestion)
    db.flush()

    normalized_events: list[Event] = []
    for row in rows:
        event = normalize_row(row, ingestion.id)
        db.add(event)
        normalized_events.append(event)

    db.flush()

    for event in normalized_events:
        for alert in create_rule_alerts(db, event):
            db.add(alert)

    db.commit()
    db.refresh(ingestion)

    return IngestionResponse(
        ingestion_id=ingestion.id,
        filename=ingestion.filename,
        records_total=ingestion.records_total,
        source_kind=ingestion.source_kind,
        status=ingestion.status,
    )


@app.get("/events", response_model=list[EventResponse])
def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Event]:
    return (
        db.query(Event)
        .order_by(Event.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@app.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    alerts = (
        db.query(Alert)
        .order_by(Alert.risk_score.desc(), Alert.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        AlertResponse(
            id=alert.id,
            event_id=alert.event_id,
            rule_name=alert.rule_name,
            severity=alert.severity,
            risk_score=alert.risk_score,
            reason_codes=json.loads(alert.reason_codes),
            created_at=alert.created_at,
            event=alert.event,
        )
        for alert in alerts
    ]


@app.get("/risk/users", response_model=list[UserRiskSummary])
def list_user_risks(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[UserRiskSummary]:
    severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    summaries: dict[str, UserRiskSummary] = {}

    events = (
        db.query(Event)
        .order_by(Event.account.asc().nulls_last(), Event.occurred_at.desc().nulls_last(), Event.id.desc())
        .all()
    )

    for event in events:
        account = event.account or "unknown"
        summary = summaries.get(account)
        if summary is None:
            summary = UserRiskSummary(
                account=account,
                event_count=0,
                alert_count=0,
                max_risk_score=0,
                max_severity="low",
                last_seen_at=event.occurred_at,
            )
            summaries[account] = summary

        summary.event_count += 1
        if event.occurred_at and (summary.last_seen_at is None or event.occurred_at > summary.last_seen_at):
            summary.last_seen_at = event.occurred_at

        for alert in event.alerts:
            summary.alert_count += 1
            if alert.risk_score > summary.max_risk_score:
                summary.max_risk_score = alert.risk_score
            if severity_rank[alert.severity] > severity_rank[summary.max_severity]:
                summary.max_severity = alert.severity

    ranked = sorted(
        summaries.values(),
        key=lambda summary: (
            summary.max_risk_score,
            severity_rank[summary.max_severity],
            summary.alert_count,
            summary.event_count,
            summary.account,
        ),
        reverse=True,
    )
    return ranked[offset : offset + limit]


@app.get("/dashboard/overview", response_model=DashboardOverview)
def dashboard_overview(db: Session = Depends(get_db)) -> DashboardOverview:
    alerts = db.query(Alert).all()
    severity_breakdown = {"low": 0, "medium": 0, "high": 0, "critical": 0}

    for alert in alerts:
        severity_breakdown[alert.severity] = severity_breakdown.get(alert.severity, 0) + 1

    return DashboardOverview(
        total_events=db.query(Event).count(),
        total_alerts=len(alerts),
        total_accounts=db.query(Event.account).filter(Event.account.is_not(None)).distinct().count(),
        high_alerts=severity_breakdown["high"],
        critical_alerts=severity_breakdown["critical"],
        severity_breakdown=severity_breakdown,
    )
