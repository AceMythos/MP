from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.config import get_settings
from app.models import AdminUser, Base


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_ingestion_error_message_column()
    _ensure_sqlite_event_ml_columns()
    _ensure_sqlite_alert_triage_status_column()
    _ensure_default_admin_user()


def _ensure_sqlite_ingestion_error_message_column() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info('ingestion_jobs')")).fetchall()
        }
        if "error_message" not in columns:
            connection.execute(text("ALTER TABLE ingestion_jobs ADD COLUMN error_message TEXT"))


def _ensure_sqlite_event_ml_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info('events')")).fetchall()}
        if "ml_anomaly_score" not in columns:
            connection.execute(text("ALTER TABLE events ADD COLUMN ml_anomaly_score FLOAT"))
        if "ml_is_anomaly" not in columns:
            connection.execute(text("ALTER TABLE events ADD COLUMN ml_is_anomaly INTEGER"))


def _ensure_sqlite_alert_triage_status_column() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info('alerts')")).fetchall()}
        if "triage_status" not in columns:
            connection.execute(text("ALTER TABLE alerts ADD COLUMN triage_status VARCHAR(30) DEFAULT 'open'"))


def check_database() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def _ensure_default_admin_user() -> None:
    with SessionLocal() as db:
        existing = db.query(AdminUser).filter(AdminUser.username == settings.admin_default_username).first()
        if existing is not None:
            return
        db.add(
            AdminUser(
                username=settings.admin_default_username,
                password_hash=hash_password(settings.admin_default_password),
            )
        )
        db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
