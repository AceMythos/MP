from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_kind: Mapped[str] = mapped_column(String(50), default="csv_upload")
    records_total: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events: Mapped[list["Event"]] = relationship(back_populates="ingestion")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingestion_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id"))
    source_type: Mapped[str] = mapped_column(String(50), default="ueba_csv")
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vlan: Mapped[str | None] = mapped_column(String(64), nullable=True)
    switch_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expected_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ingestion: Mapped[IngestionJob] = relationship(back_populates="events")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="event")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    rule_name: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[int] = mapped_column(Integer)
    reason_codes: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped[Event] = relationship(back_populates="alerts")
