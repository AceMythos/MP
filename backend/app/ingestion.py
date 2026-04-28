import csv
import io
import json
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import Alert
from app.models import Event


DATASET_FIELD_MAP = {
    "id": "external_id",
    "account": "account",
    "group": "group_name",
    "IP": "source_ip",
    "url": "url",
    "port": "port",
    "vlan": "vlan",
    "switchIP": "switch_ip",
    "time": "occurred_at",
    "ret": "expected_risk",
}

REQUIRED_CSV_FIELDS = {"id", "account", "group", "IP", "url", "port", "vlan", "switchIP", "time"}


def parse_csv_bytes(payload: bytes) -> list[dict[str, str]]:
    if not payload.strip():
        raise ValueError("CSV file is empty.")

    decoded = payload.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded))
    if reader.fieldnames is None:
        raise ValueError("CSV header row is missing.")

    missing_fields = sorted(REQUIRED_CSV_FIELDS.difference(set(reader.fieldnames)))
    if missing_fields:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_fields)}")

    return [dict(row) for row in reader]


def normalize_row(row: dict[str, str], ingestion_id: int, row_number: int) -> Event:
    normalized: dict[str, object] = {
        "ingestion_id": ingestion_id,
        "source_type": "ueba_csv",
        "raw_payload": json.dumps(row, ensure_ascii=True),
    }

    for source_field, target_field in DATASET_FIELD_MAP.items():
        value = row.get(source_field)
        if value is None or value == "":
            continue

        cleaned_value = value.strip() if isinstance(value, str) else value

        if target_field == "port":
            normalized[target_field] = _parse_int(cleaned_value, "port", row_number)
        elif target_field == "occurred_at":
            normalized[target_field] = _parse_datetime(cleaned_value, "time", row_number)
        elif target_field == "expected_risk":
            normalized[target_field] = _parse_float(cleaned_value, "ret", row_number)
        else:
            normalized[target_field] = cleaned_value

    return Event(**normalized)


def create_rule_alerts(db: Session, event: Event) -> list[Alert]:
    reason_codes: list[str] = []
    score = 0

    if not event.account:
        reason_codes.append("missing_account")
        score += 15
    if not event.source_ip:
        reason_codes.append("missing_source_ip")
        score += 15
    if not event.occurred_at:
        reason_codes.append("missing_timestamp")
        score += 10

    if event.occurred_at and (event.occurred_at.hour < 6 or event.occurred_at.hour >= 22):
        reason_codes.append("activity_outside_standard_hours")
        score += 20

    if event.url:
        hostname = (urlparse(event.url).hostname or "").lower()
        if any(flag in hostname for flag in ("admin", "secure", "internal", "vpn")):
            reason_codes.append("sensitive_or_internal_url_target")
            score += 15

    if event.account:
        prior_events = (
            db.query(Event)
            .filter(Event.account == event.account, Event.id < event.id)
            .all()
        )

        seen_ips = {prior.source_ip for prior in prior_events if prior.source_ip}
        if event.source_ip and len(prior_events) >= 3 and event.source_ip not in seen_ips:
            reason_codes.append("new_source_ip_for_account")
            score += 25

        seen_ports = {prior.port for prior in prior_events if prior.port is not None}
        if event.port is not None and len(seen_ports) >= 2 and event.port not in seen_ports:
            reason_codes.append("unusual_port_for_account")
            score += 15

        seen_vlans = {prior.vlan for prior in prior_events if prior.vlan}
        if event.vlan and len(seen_vlans) >= 2 and event.vlan not in seen_vlans:
            reason_codes.append("unusual_vlan_for_account")
            score += 10

    if not reason_codes:
        return []

    score = min(score, 100)
    if score >= 70:
        severity = "critical"
    elif score >= 50:
        severity = "high"
    elif score >= 30:
        severity = "medium"
    else:
        severity = "low"

    return [
        Alert(
            event_id=event.id,
            rule_name="hybrid_rule_pack_v1",
            severity=severity,
            risk_score=score,
            reason_codes=json.dumps(reason_codes, ensure_ascii=True),
        )
    ]


def _parse_int(value: object, field_name: str, row_number: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid integer value for '{field_name}' at CSV row {row_number}: {value!r}"
        ) from exc


def _parse_float(value: object, field_name: str, row_number: int) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid float value for '{field_name}' at CSV row {row_number}: {value!r}"
        ) from exc


def _parse_datetime(value: object, field_name: str, row_number: int) -> datetime:
    if not isinstance(value, str):
        raise ValueError(
            f"Invalid datetime value for '{field_name}' at CSV row {row_number}: {value!r}"
        )

    try:
        return datetime.strptime(value, "%Y/%m/%d %H:%M")
    except ValueError as exc:
        raise ValueError(
            f"Invalid datetime value for '{field_name}' at CSV row {row_number}: {value!r}. "
            "Expected format: YYYY/M/D HH:MM"
        ) from exc
