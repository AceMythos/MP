from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Base


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_ingestion_error_message_column()
    _ensure_sqlite_event_ml_columns()


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


def check_database() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
