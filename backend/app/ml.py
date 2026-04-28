import json
from urllib.parse import urlparse

import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.models import Alert, Event


def run_isolation_forest_detection(
    db: Session, contamination: float = 0.1
) -> tuple[int, int, int, int]:
    events = db.query(Event).order_by(Event.id.asc()).all()
    if not events:
        return 0, 0, 0, 0

    frame = pd.DataFrame(
        [
            {
                "event_id": event.id,
                "account": event.account or "unknown",
                "group_name": event.group_name or "unknown",
                "source_ip": event.source_ip or "unknown",
                "url_host": (urlparse(event.url).hostname if event.url else None) or "unknown",
                "port": event.port if event.port is not None else -1,
                "vlan": event.vlan or "unknown",
                "switch_ip": event.switch_ip or "unknown",
                "hour": event.occurred_at.hour if event.occurred_at else -1,
                "weekday": event.occurred_at.weekday() if event.occurred_at else -1,
            }
            for event in events
        ]
    )

    encoded = pd.DataFrame(index=frame.index)
    for column in ("account", "group_name", "source_ip", "url_host", "vlan", "switch_ip"):
        encoded[f"{column}_code"] = pd.factorize(frame[column])[0]
    encoded["port"] = frame["port"]
    encoded["hour"] = frame["hour"]
    encoded["weekday"] = frame["weekday"]

    # IsolationForest needs contamination in (0, 0.5].
    capped_contamination = min(max(contamination, 0.001), 0.5)
    model = IsolationForest(
        contamination=capped_contamination,
        random_state=42,
        n_estimators=200,
    )
    predictions = model.fit_predict(encoded)
    raw_scores = -model.decision_function(encoded)

    min_score = float(raw_scores.min())
    max_score = float(raw_scores.max())
    spread = max_score - min_score
    if spread == 0:
        normalized_scores = [0.0 for _ in raw_scores]
    else:
        normalized_scores = [float((score - min_score) / spread) for score in raw_scores]

    alerts_created = 0
    anomaly_events = 0

    for event, prediction, ml_score in zip(events, predictions, normalized_scores):
        is_anomaly = 1 if prediction == -1 else 0
        event.ml_anomaly_score = ml_score
        event.ml_is_anomaly = is_anomaly

        if is_anomaly == 0:
            continue

        anomaly_events += 1
        existing_alert = (
            db.query(Alert)
            .filter(Alert.event_id == event.id, Alert.rule_name == "isolation_forest_v1")
            .first()
        )
        if existing_alert is not None:
            continue

        risk_score = min(100, max(40, int(round(40 + ml_score * 60))))
        if risk_score >= 80:
            severity = "critical"
        elif risk_score >= 60:
            severity = "high"
        elif risk_score >= 45:
            severity = "medium"
        else:
            severity = "low"

        db.add(
            Alert(
                event_id=event.id,
                rule_name="isolation_forest_v1",
                severity=severity,
                risk_score=risk_score,
                reason_codes=json.dumps(["ml_isolation_forest_anomaly"], ensure_ascii=True),
            )
        )
        alerts_created += 1

    combined_alerts_created = _create_combined_risk_alerts(db=db, events=events)
    db.commit()
    return len(events), anomaly_events, alerts_created, combined_alerts_created


def _create_combined_risk_alerts(db: Session, events: list[Event]) -> int:
    created = 0
    for event in events:
        rule_alerts = [
            alert for alert in event.alerts if alert.rule_name not in {"isolation_forest_v1", "combined_risk_v1"}
        ]
        max_rule_score = max((alert.risk_score for alert in rule_alerts), default=0)

        ml_score_100 = int(round((event.ml_anomaly_score or 0.0) * 100))
        ml_bonus = 15 if event.ml_is_anomaly == 1 else 0
        combined_score = min(100, int(round((max_rule_score * 0.6) + (ml_score_100 * 0.4) + ml_bonus)))

        if combined_score < 30:
            continue

        inherited_reasons: list[str] = []
        for alert in rule_alerts:
            try:
                inherited_reasons.extend(json.loads(alert.reason_codes))
            except json.JSONDecodeError:
                continue
        inherited_reasons = sorted(set(inherited_reasons))

        reason_codes = ["combined_risk_v1", f"rule_score_{max_rule_score}", f"ml_score_{ml_score_100}"]
        if event.ml_is_anomaly == 1:
            reason_codes.append("ml_isolation_forest_anomaly")
        reason_codes.extend(inherited_reasons)

        existing_alert = (
            db.query(Alert).filter(Alert.event_id == event.id, Alert.rule_name == "combined_risk_v1").first()
        )
        severity = _score_to_severity(combined_score)
        if existing_alert is None:
            db.add(
                Alert(
                    event_id=event.id,
                    rule_name="combined_risk_v1",
                    severity=severity,
                    risk_score=combined_score,
                    reason_codes=json.dumps(reason_codes, ensure_ascii=True),
                )
            )
            created += 1
            continue

        existing_alert.severity = severity
        existing_alert.risk_score = combined_score
        existing_alert.reason_codes = json.dumps(reason_codes, ensure_ascii=True)

    return created


def _score_to_severity(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"
