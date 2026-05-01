from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import IngestionJob


def _upload_csv(client: TestClient, auth_headers: dict[str, str], csv_payload: str, filename: str = "sample.csv"):
    return client.post(
        "/ingestions/csv",
        files={"file": (filename, csv_payload.encode("utf-8"), "text/csv")},
        headers=auth_headers,
    )


def test_csv_ingestion_and_event_listing(client: TestClient, auth_headers: dict[str, str]) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,8080,700,10.0.0.1,2021/6/16 7:56,0.1149\n"
    )

    response = _upload_csv(client, auth_headers, sample_csv)
    assert response.status_code == 200
    body = response.json()
    assert body["records_total"] == 1
    assert body["status"] == "completed"
    assert body["error_message"] is None

    events_response = client.get("/events", headers=auth_headers)
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) == 1
    assert events[0]["account"] == "user@example.com"
    assert events[0]["source_ip"] == "192.168.1.10"
    assert events[0]["port"] == 8080

    alerts_response = client.get("/alerts", headers=auth_headers)
    assert alerts_response.status_code == 200
    assert alerts_response.json() == []


def test_rule_engine_flags_new_ip_for_established_account(client: TestClient, auth_headers: dict[str, str]) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/16 08:30,0.1149\n"
        "2,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/17 08:35,0.1149\n"
        "3,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/18 08:40,0.1149\n"
        "4,user@example.com,engineering,10.20.30.40,http://internal.example.com,8443,999,10.0.0.2,2021/6/19 23:15,0.1149\n"
    )

    response = _upload_csv(client, auth_headers, sample_csv)
    assert response.status_code == 200
    assert response.json()["records_total"] == 4

    alerts_response = client.get("/alerts", headers=auth_headers)
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["severity"] == "high"
    assert "new_source_ip_for_account" in alert["reason_codes"]
    assert "activity_outside_standard_hours" in alert["reason_codes"]
    assert "sensitive_or_internal_url_target" in alert["reason_codes"]


def test_user_risk_summary_ranks_accounts_by_alert_score(client: TestClient, auth_headers: dict[str, str]) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,low@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/16 10:30,0.1149\n"
        "2,high@example.com,engineering,192.168.1.10,http://internal.example.com,443,700,10.0.0.1,2021/6/17 23:35,0.1149\n"
        "3,high@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/18 08:40,0.1149\n"
        "4,high@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/19 08:45,0.1149\n"
        "5,high@example.com,engineering,10.20.30.40,http://internal.example.com,8443,999,10.0.0.2,2021/6/20 23:15,0.1149\n"
    )

    response = _upload_csv(client, auth_headers, sample_csv)
    assert response.status_code == 200

    summaries_response = client.get("/risk/users", headers=auth_headers)
    assert summaries_response.status_code == 200
    summaries = summaries_response.json()
    assert len(summaries) == 2
    assert summaries[0]["account"] == "high@example.com"
    assert summaries[0]["alert_count"] == 2
    assert summaries[0]["max_severity"] == "high"
    assert summaries[0]["max_risk_score"] == 60
    assert summaries[1]["account"] == "low@example.com"
    assert summaries[1]["alert_count"] == 0
    assert summaries[1]["max_risk_score"] == 0


def test_dashboard_overview_returns_security_summary_counts(client: TestClient, auth_headers: dict[str, str]) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,quiet@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/16 10:30,0.1149\n"
        "2,risky@example.com,engineering,192.168.1.10,http://internal.example.com,443,700,10.0.0.1,2021/6/17 23:35,0.1149\n"
        "3,risky@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/18 08:40,0.1149\n"
        "4,risky@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/19 08:45,0.1149\n"
        "5,risky@example.com,engineering,10.20.30.40,http://internal.example.com,8443,999,10.0.0.2,2021/6/20 23:15,0.1149\n"
    )

    response = _upload_csv(client, auth_headers, sample_csv)
    assert response.status_code == 200

    overview_response = client.get("/dashboard/overview", headers=auth_headers)
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["total_events"] == 5
    assert overview["total_alerts"] == 2
    assert overview["total_accounts"] == 2
    assert overview["high_alerts"] == 1
    assert overview["critical_alerts"] == 0
    assert overview["severity_breakdown"] == {
        "low": 0,
        "medium": 1,
        "high": 1,
        "critical": 0,
    }


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"


def test_login_success_returns_bearer_token(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert isinstance(payload["access_token"], str)
    assert len(payload["access_token"]) > 20


def test_protected_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.get("/events")
    assert response.status_code == 401


def test_csv_ingestion_marks_job_failed_for_invalid_port(client: TestClient, auth_headers: dict[str, str]) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,not-a-port,700,10.0.0.1,2021/6/16 7:56,0.1149\n"
    )

    response = _upload_csv(client, auth_headers, sample_csv, filename="bad.csv")
    assert response.status_code == 400
    assert "Invalid integer value for 'port'" in response.json()["detail"]

    db = SessionLocal()
    try:
        job = db.query(IngestionJob).one()
        assert job.status == "failed"
        assert job.error_message is not None
        assert "Invalid integer value for 'port'" in job.error_message
    finally:
        db.close()


def test_csv_ingestion_rejects_missing_required_columns(client: TestClient, auth_headers: dict[str, str]) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,time\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,443,700,2021/6/16 7:56\n"
    )

    response = _upload_csv(client, auth_headers, sample_csv, filename="missing-columns.csv")
    assert response.status_code == 400
    assert "CSV is missing required columns" in response.json()["detail"]

    db = SessionLocal()
    try:
        job = db.query(IngestionJob).one()
        assert job.status == "failed"
        assert job.error_message is not None
    finally:
        db.close()


def test_isolation_forest_detection_scores_events_and_creates_ml_alerts(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/16 08:30,0.1\n"
        "2,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/17 08:30,0.1\n"
        "3,user@example.com,engineering,192.168.1.11,http://example.com,443,700,10.0.0.1,2021/6/18 08:30,0.1\n"
        "4,user@example.com,engineering,192.168.1.12,http://example.com,443,700,10.0.0.1,2021/6/19 08:30,0.1\n"
        "5,user@example.com,engineering,10.20.30.40,http://internal.example.com,9999,900,10.0.0.2,2021/6/20 23:15,0.1\n"
    )

    ingest_response = _upload_csv(client, auth_headers, sample_csv)
    assert ingest_response.status_code == 200

    detect_response = client.post("/detections/isolation-forest", headers=auth_headers)
    assert detect_response.status_code == 200
    detection_body = detect_response.json()
    assert detection_body["processed_events"] == 5
    assert detection_body["anomaly_events"] >= 1
    assert detection_body["alerts_created"] >= 1
    assert detection_body["combined_alerts_created"] >= 1

    events_response = client.get("/events", headers=auth_headers)
    assert events_response.status_code == 200
    events = events_response.json()
    assert all(event["ml_anomaly_score"] is not None for event in events)
    assert all(event["ml_is_anomaly"] in (0, 1) for event in events)

    alerts_response = client.get("/alerts", headers=auth_headers)
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()
    assert any(alert["rule_name"] == "isolation_forest_v1" for alert in alerts)
    combined_alerts = [alert for alert in alerts if alert["rule_name"] == "combined_risk_v1"]
    assert combined_alerts
    assert all("combined_risk_v1" in alert["reason_codes"] for alert in combined_alerts)


def test_isolation_forest_detection_is_idempotent_for_alert_creation(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/16 08:30,0.1\n"
        "2,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/17 08:30,0.1\n"
        "3,user@example.com,engineering,10.20.30.40,http://internal.example.com,9999,900,10.0.0.2,2021/6/20 23:15,0.1\n"
    )

    ingest_response = _upload_csv(client, auth_headers, sample_csv)
    assert ingest_response.status_code == 200

    first_run = client.post("/detections/isolation-forest", headers=auth_headers)
    assert first_run.status_code == 200
    second_run = client.post("/detections/isolation-forest", headers=auth_headers)
    assert second_run.status_code == 200
    assert second_run.json()["alerts_created"] == 0
    assert second_run.json()["combined_alerts_created"] == 0
