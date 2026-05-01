import json

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_access_token, verify_password
from app.config import get_settings
from app.db import check_database, get_db, init_database
from app.ingestion import create_rule_alerts, normalize_row, parse_csv_bytes
from app.ml import run_isolation_forest_detection
from app.models import AdminAuditLog, AdminUser, Alert, Event, IngestionJob
from app.schemas import (
    AlertStatusUpdateRequest,
    AdminAuditLogResponse,
    AlertResponse,
    DashboardOverview,
    DetectionEvaluationResponse,
    EventAlertDetail,
    EventExplanationResponse,
    EventResponse,
    HealthResponse,
    IngestionResponse,
    LoginRequest,
    LoginResponse,
    MlDetectionResponse,
    UserRiskSummary,
)
from app.synthetic import generate_synthetic_events


settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
init_database()
security = HTTPBearer(auto_error=False)


def _create_audit_log(db: Session, admin_username: str, action: str, details: str | None = None) -> None:
    db.add(AdminAuditLog(admin_username=admin_username, action=action, details=details))


def get_current_admin_username(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required.")
    username = verify_access_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")
    return username


def _score_to_severity(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> dict[str, str]:
    database_ok = check_database()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "database": "ok" if database_ok else "down",
    }


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    admin = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    _create_audit_log(db=db, admin_username=admin.username, action="admin_login_success")
    db.commit()
    return LoginResponse(access_token=create_access_token(admin.username))


@app.post("/ingestions/csv", response_model=IngestionResponse)
def ingest_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin_username),
) -> IngestionResponse:
    ingestion = IngestionJob(
        filename=file.filename or "upload.csv",
        source_kind="csv_upload",
        records_total=0,
        status="processing",
    )
    db.add(ingestion)
    db.commit()
    db.refresh(ingestion)
    try:
        payload = file.file.read()
        rows = parse_csv_bytes(payload)
        ingestion.records_total = len(rows)

        for row_number, row in enumerate(rows, start=2):
            event = normalize_row(row, ingestion.id, row_number=row_number)
            db.add(event)
            db.flush()

            for alert in create_rule_alerts(db, event):
                db.add(alert)

        ingestion.status = "completed"
        ingestion.error_message = None
        _create_audit_log(
            db=db,
            admin_username=admin_username,
            action="csv_ingestion_completed",
            details=f"filename={ingestion.filename} records={ingestion.records_total}",
        )
        db.commit()
        db.refresh(ingestion)
    except ValueError as exc:
        db.rollback()
        failed_ingestion = db.get(IngestionJob, ingestion.id)
        if failed_ingestion is not None:
            failed_ingestion.status = "failed"
            failed_ingestion.error_message = str(exc)
            db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        failed_ingestion = db.get(IngestionJob, ingestion.id)
        if failed_ingestion is not None:
            failed_ingestion.status = "failed"
            failed_ingestion.error_message = str(exc)
            db.commit()
        raise HTTPException(status_code=500, detail="Failed to process CSV ingestion.") from exc

    return IngestionResponse(
        ingestion_id=ingestion.id,
        filename=ingestion.filename,
        records_total=ingestion.records_total,
        source_kind=ingestion.source_kind,
        status=ingestion.status,
        error_message=ingestion.error_message,
    )


@app.get("/events", response_model=list[EventResponse])
def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin_username),
) -> list[Event]:
    return (
        db.query(Event)
        .order_by(Event.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@app.get("/events/{event_id}/explanation", response_model=EventExplanationResponse)
def get_event_explanation(
    event_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin_username),
) -> EventExplanationResponse:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    rule_alerts = [a for a in event.alerts if a.rule_name not in {"isolation_forest_v1", "combined_risk_v1"}]
    max_rule_score = max((a.risk_score for a in rule_alerts), default=0)
    ml_score_100 = int(round((event.ml_anomaly_score or 0.0) * 100))
    ml_bonus = 15 if event.ml_is_anomaly == 1 else 0
    combined_score = min(100, int(round((max_rule_score * 0.6) + (ml_score_100 * 0.4) + ml_bonus)))
    combined_severity = _score_to_severity(combined_score)

    alert_details: list[EventAlertDetail] = []
    for alert in sorted(event.alerts, key=lambda a: (a.risk_score, a.created_at), reverse=True):
        try:
            reasons = json.loads(alert.reason_codes)
        except json.JSONDecodeError:
            reasons = []
        alert_details.append(
            EventAlertDetail(
                rule_name=alert.rule_name,
                severity=alert.severity,
                risk_score=alert.risk_score,
                reason_codes=reasons,
                created_at=alert.created_at,
            )
        )

    return EventExplanationResponse(
        event_id=event.id,
        account=event.account,
        source_ip=event.source_ip,
        occurred_at=event.occurred_at,
        ml_anomaly_score=event.ml_anomaly_score,
        ml_is_anomaly=event.ml_is_anomaly,
        max_rule_score=max_rule_score,
        ml_score_100=ml_score_100,
        ml_bonus=ml_bonus,
        combined_score=combined_score,
        combined_severity=combined_severity,
        alerts=alert_details,
    )


@app.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin_username),
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
            triage_status=alert.triage_status,
            risk_score=alert.risk_score,
            reason_codes=json.loads(alert.reason_codes),
            created_at=alert.created_at,
            event=alert.event,
        )
        for alert in alerts
    ]


@app.patch("/alerts/{alert_id}/status", response_model=AlertResponse)
def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin_username),
) -> AlertResponse:
    allowed_statuses = {"open", "acknowledged", "in_progress", "escalated", "resolved"}
    next_status = payload.triage_status.strip().lower()
    if next_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid triage_status. Allowed: {', '.join(sorted(allowed_statuses))}")

    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")

    previous_status = alert.triage_status
    alert.triage_status = next_status
    _create_audit_log(
        db=db,
        admin_username=admin_username,
        action="alert_triage_status_updated",
        details=f"alert_id={alert.id} from={previous_status} to={next_status}",
    )
    db.commit()
    db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        event_id=alert.event_id,
        rule_name=alert.rule_name,
        severity=alert.severity,
        triage_status=alert.triage_status,
        risk_score=alert.risk_score,
        reason_codes=json.loads(alert.reason_codes),
        created_at=alert.created_at,
        event=alert.event,
    )


@app.get("/risk/users", response_model=list[UserRiskSummary])
def list_user_risks(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin_username),
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
def dashboard_overview(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin_username),
) -> DashboardOverview:
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


@app.get("/admin/audit-logs", response_model=list[AdminAuditLogResponse])
def list_admin_audit_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin_username),
) -> list[AdminAuditLog]:
    return (
        db.query(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@app.post("/ingestions/synthetic", response_model=IngestionResponse)
def ingest_synthetic(
    count: int = Query(default=200, ge=1, le=5000),
    seed: int | None = Query(default=None),
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin_username),
) -> IngestionResponse:
    ingestion = IngestionJob(
        filename=f"synthetic_{count}.csv",
        source_kind="synthetic_ueba",
        records_total=0,
        status="processing",
    )
    db.add(ingestion)
    db.commit()
    db.refresh(ingestion)

    try:
        events = generate_synthetic_events(ingestion_id=ingestion.id, count=count, seed=seed)
        ingestion.records_total = len(events)
        for event in events:
            db.add(event)
            db.flush()
            for alert in create_rule_alerts(db, event):
                db.add(alert)
        ingestion.status = "completed"
        _create_audit_log(
            db=db,
            admin_username=admin_username,
            action="synthetic_ingestion_completed",
            details=f"count={count} seed={seed}",
        )
        db.commit()
        db.refresh(ingestion)
    except Exception as exc:
        db.rollback()
        failed_ingestion = db.get(IngestionJob, ingestion.id)
        if failed_ingestion is not None:
            failed_ingestion.status = "failed"
            failed_ingestion.error_message = str(exc)
            db.commit()
        raise HTTPException(status_code=500, detail="Failed to generate synthetic events.") from exc

    return IngestionResponse(
        ingestion_id=ingestion.id,
        filename=ingestion.filename,
        records_total=ingestion.records_total,
        source_kind=ingestion.source_kind,
        status=ingestion.status,
        error_message=ingestion.error_message,
    )


@app.post("/detections/isolation-forest", response_model=MlDetectionResponse)
def run_ml_detection(
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin_username),
) -> MlDetectionResponse:
    processed_events, anomaly_events, alerts_created, combined_alerts_created = run_isolation_forest_detection(db=db)
    _create_audit_log(
        db=db,
        admin_username=admin_username,
        action="ml_detection_run",
        details=f"processed={processed_events} anomalies={anomaly_events} ml_alerts={alerts_created}",
    )
    db.commit()
    return MlDetectionResponse(
        processed_events=processed_events,
        anomaly_events=anomaly_events,
        alerts_created=alerts_created,
        combined_alerts_created=combined_alerts_created,
    )


@app.post("/detections/evaluate", response_model=DetectionEvaluationResponse)
def evaluate_detections(
    db: Session = Depends(get_db),
    admin_username: str = Depends(get_current_admin_username),
) -> DetectionEvaluationResponse:
    events = db.query(Event).all()
    alerts = db.query(Alert).all()

    total_events = len(events)
    total_alerts = len(alerts)
    alerts_per_1000_events = round((total_alerts / total_events) * 1000, 2) if total_events else 0.0

    severity_breakdown = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    reason_counts: dict[str, int] = {}
    account_risk: dict[str, int] = {}

    event_by_id = {event.id: event for event in events}
    for alert in alerts:
        severity_breakdown[alert.severity] = severity_breakdown.get(alert.severity, 0) + 1

        try:
            reasons = json.loads(alert.reason_codes)
        except json.JSONDecodeError:
            reasons = []
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        event = event_by_id.get(alert.event_id)
        account = event.account if event and event.account else "unknown"
        account_risk[account] = account_risk.get(account, 0) + alert.risk_score

    top_reason_codes = [
        {"reason_code": reason, "count": count}
        for reason, count in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)[:8]
    ]
    top_risky_accounts = [
        {"account": account, "risk_score_sum": score}
        for account, score in sorted(account_risk.items(), key=lambda item: item[1], reverse=True)[:8]
    ]

    _create_audit_log(
        db=db,
        admin_username=admin_username,
        action="detection_evaluation_run",
        details=f"events={total_events} alerts={total_alerts}",
    )
    db.commit()

    return DetectionEvaluationResponse(
        total_events=total_events,
        total_alerts=total_alerts,
        alerts_per_1000_events=alerts_per_1000_events,
        severity_breakdown=severity_breakdown,
        top_reason_codes=top_reason_codes,
        top_risky_accounts=top_risky_accounts,
    )
