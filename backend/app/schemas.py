from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    database: str


class IngestionResponse(BaseModel):
    ingestion_id: int
    filename: str
    records_total: int
    source_kind: str
    status: str
    error_message: str | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingestion_id: int
    source_type: str
    external_id: str | None
    account: str | None
    group_name: str | None
    source_ip: str | None
    url: str | None
    port: int | None
    vlan: str | None
    switch_ip: str | None
    occurred_at: datetime | None
    expected_risk: float | None
    ml_anomaly_score: float | None
    ml_is_anomaly: int | None
    raw_payload: str
    created_at: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    rule_name: str
    severity: str
    risk_score: int
    reason_codes: list[str]
    created_at: datetime
    event: EventResponse


class UserRiskSummary(BaseModel):
    account: str
    event_count: int
    alert_count: int
    max_risk_score: int
    max_severity: str
    last_seen_at: datetime | None


class DashboardOverview(BaseModel):
    total_events: int
    total_alerts: int
    total_accounts: int
    high_alerts: int
    critical_alerts: int
    severity_breakdown: dict[str, int]


class MlDetectionResponse(BaseModel):
    processed_events: int
    anomaly_events: int
    alerts_created: int
    combined_alerts_created: int


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_username: str
    action: str
    details: str | None
    created_at: datetime
