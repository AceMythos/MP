from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import engine, init_database
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    init_database()


@pytest.fixture
def client() -> TestClient:
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
