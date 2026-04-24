from io import BytesIO

from app.db import SessionLocal, engine, init_database
from app.models import Alert, Base, Event
from app.main import healthcheck, ingest_csv, list_alerts, list_events, list_user_risks
from fastapi import UploadFile


def test_csv_ingestion_and_event_listing() -> None:
    Base.metadata.drop_all(bind=engine)
    init_database()

    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,8080,700,10.0.0.1,2021/6/16 7:56,0.1149\n"
    )

    db = SessionLocal()
    try:
        upload = UploadFile(filename="sample.csv", file=BytesIO(sample_csv.encode("utf-8")))
        response = ingest_csv(file=upload, db=db)
        assert response.records_total == 1

        payload = list_events(limit=100, offset=0, db=db)
        assert len(payload) == 1
        assert payload[0].account == "user@example.com"
        assert payload[0].source_ip == "192.168.1.10"
        assert payload[0].port == 8080

        assert db.query(Event).count() == 1
        assert db.query(Alert).count() == 0
        assert list_alerts(limit=100, offset=0, db=db) == []
    finally:
        db.close()


def test_rule_engine_flags_new_ip_for_established_account() -> None:
    Base.metadata.drop_all(bind=engine)
    init_database()

    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/16 08:30,0.1149\n"
        "2,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/17 08:35,0.1149\n"
        "3,user@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/18 08:40,0.1149\n"
        "4,user@example.com,engineering,10.20.30.40,http://internal.example.com,8443,999,10.0.0.2,2021/6/19 23:15,0.1149\n"
    )

    db = SessionLocal()
    try:
        upload = UploadFile(filename="sample.csv", file=BytesIO(sample_csv.encode("utf-8")))
        response = ingest_csv(file=upload, db=db)
        assert response.records_total == 4

        alerts_payload = list_alerts(limit=100, offset=0, db=db)
        assert len(alerts_payload) == 1
        alert = alerts_payload[0]
        assert alert.severity == "high"
        assert "new_source_ip_for_account" in alert.reason_codes
        assert "activity_outside_standard_hours" in alert.reason_codes
        assert "sensitive_or_internal_url_target" in alert.reason_codes
    finally:
        db.close()


def test_user_risk_summary_ranks_accounts_by_alert_score() -> None:
    Base.metadata.drop_all(bind=engine)
    init_database()

    sample_csv = (
        "id,account,group,IP,url,port,vlan,switchIP,time,ret\n"
        "1,low@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/16 10:30,0.1149\n"
        "2,high@example.com,engineering,192.168.1.10,http://internal.example.com,443,700,10.0.0.1,2021/6/17 23:35,0.1149\n"
        "3,high@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/18 08:40,0.1149\n"
        "4,high@example.com,engineering,192.168.1.10,http://example.com,443,700,10.0.0.1,2021/6/19 08:45,0.1149\n"
        "5,high@example.com,engineering,10.20.30.40,http://internal.example.com,8443,999,10.0.0.2,2021/6/20 23:15,0.1149\n"
    )

    db = SessionLocal()
    try:
        upload = UploadFile(filename="sample.csv", file=BytesIO(sample_csv.encode("utf-8")))
        ingest_csv(file=upload, db=db)

        summaries = list_user_risks(limit=100, offset=0, db=db)
        assert len(summaries) == 2
        assert summaries[0].account == "high@example.com"
        assert summaries[0].alert_count == 2
        assert summaries[0].max_severity == "high"
        assert summaries[0].max_risk_score == 60
        assert summaries[1].account == "low@example.com"
        assert summaries[1].alert_count == 0
        assert summaries[1].max_risk_score == 0
    finally:
        db.close()


def test_healthcheck() -> None:
    payload = healthcheck()

    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
