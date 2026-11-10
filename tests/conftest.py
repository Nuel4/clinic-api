from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clock import get_now
from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app

# Frozen "now": Monday 1 June 2026, 07:00 UTC (08:00 in Lisbon, which is UTC+1 in summer).
NOW = datetime(2026, 6, 1, 7, 0, tzinfo=UTC)
MONDAY = "2026-06-01"
NEXT_MONDAY = "2026-06-08"
TUESDAY = "2026-06-02"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield session_factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session):
    def override_db():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_now] = lambda: NOW
    app.dependency_overrides[get_settings] = lambda: Settings(clinic_timezone="Europe/Lisbon")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def doctor(client):
    """A doctor working Mondays 09:00-12:00 and 14:00-17:00 Lisbon time."""
    response = client.post("/api/doctors", json={"full_name": "Dr. Ana Exemplo", "specialty": "general"})
    assert response.status_code == 201
    doctor = response.json()
    for start, end in [("09:00", "12:00"), ("14:00", "17:00")]:
        r = client.post(
            f"/api/doctors/{doctor['id']}/availability",
            json={"weekday": 0, "start_time": start, "end_time": end},
        )
        assert r.status_code == 201
    return doctor


@pytest.fixture
def patient(client):
    response = client.post(
        "/api/patients", json={"full_name": "Test Patient", "email": "patient@example.com"}
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def book(client, doctor, patient):
    """Book with sensible defaults; override any field by keyword."""

    def _book(**overrides):
        payload = {
            "doctor_id": doctor["id"],
            "patient_id": patient["id"],
            "starts_at": f"{MONDAY}T09:00:00+01:00",
            "duration_minutes": 30,
        }
        payload.update(overrides)
        return client.post("/api/appointments", json=payload)

    return _book
