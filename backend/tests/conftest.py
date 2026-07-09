import os
import sys
from pathlib import Path

# Make `import app...` work when pytest is run from the backend/ directory
# without needing the package installed in editable mode.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Guarantee a JWT secret is available even in a fresh clone with no .env file,
# and do it before the first import of app.config/app.main so Settings()
# picks it up at construction time.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.models import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    """A TestClient wired to a fresh temp-file SQLite DB per test - shared
    across all router test modules so each test gets full request ->
    validation -> DB -> response isolation without hitting the real dev DB.
    """
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture()
def auth_headers(client):
    """Signs up and logs in a fresh user, returning ready-to-use auth headers."""
    client.post(
        "/auth/signup",
        json={"email": "fixture-user@example.com", "password": "roadwarrior123", "full_name": "Fixture User"},
    )
    login = client.post(
        "/auth/login", data={"username": "fixture-user@example.com", "password": "roadwarrior123"}
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
