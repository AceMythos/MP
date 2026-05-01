from __future__ import annotations

import random
from datetime import datetime, timedelta

from app.models import Event


def generate_synthetic_events(ingestion_id: int, count: int, seed: int | None = None) -> list[Event]:
    rng = random.Random(seed)
    base_time = datetime.utcnow() - timedelta(days=7)

    accounts = [f"user{i}@example.com" for i in range(1, 13)]
    groups = ["engineering", "finance", "it-admin", "ops", "hr"]
    normal_ports = [80, 443, 8080]
    abnormal_ports = [22, 3389, 5985, 3306, 5432]
    vlans = ["100", "200", "300", "700"]
    switches = ["10.10.0.1", "10.10.0.2", "10.10.1.1", "10.10.2.1"]

    events: list[Event] = []
    for idx in range(count):
        account = rng.choice(accounts)
        group_name = rng.choice(groups)
        hour = rng.choices([9, 10, 11, 14, 16, 20, 23, 2], weights=[18, 18, 18, 16, 16, 7, 4, 3], k=1)[0]
        minute = rng.randint(0, 59)
        occurred_at = base_time + timedelta(minutes=idx * 15)
        occurred_at = occurred_at.replace(hour=hour, minute=minute)

        anomaly_bias = rng.random()
        if anomaly_bias < 0.14:
            source_ip = f"172.16.{rng.randint(0, 30)}.{rng.randint(1, 254)}"
            port = rng.choice(abnormal_ports)
            url = rng.choice(
                [
                    "http://internal.example.com/admin",
                    "http://vpn.example.com/secure",
                    "http://secure.example.com/internal",
                ]
            )
            vlan = rng.choice(["900", "999"])
        else:
            source_ip = f"192.168.{rng.randint(1, 8)}.{rng.randint(2, 250)}"
            port = rng.choice(normal_ports)
            url = rng.choice(
                [
                    "http://example.com",
                    "http://portal.example.com",
                    "http://status.example.com",
                    "http://intranet.example.com",
                ]
            )
            vlan = rng.choice(vlans)

        event = Event(
            ingestion_id=ingestion_id,
            source_type="ueba_synthetic",
            external_id=f"syn-{idx+1}",
            account=account,
            group_name=group_name,
            source_ip=source_ip,
            url=url,
            port=port,
            vlan=vlan,
            switch_ip=rng.choice(switches),
            occurred_at=occurred_at,
            raw_payload='{"synthetic":true}',
        )
        events.append(event)

    return events
