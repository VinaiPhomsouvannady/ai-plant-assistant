import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app


def test_runtime_env_keeps_container_database_url(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+psycopg://plantops:plantops@localhost:5432/plantops\n")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://plantops:plantops@db:5432/plantops")

    sys.modules.pop("backend.app", None)
    app_module = importlib.import_module("backend.app")

    assert os.environ["DATABASE_URL"] == "postgresql+psycopg://plantops:plantops@db:5432/plantops"
    assert app_module.store.engine is None
    assert app_module.store.SessionLocal is None


def test_health_and_seeded_documents() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["documents"] == 3


def test_troubleshooting_returns_citations() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/troubleshoot",
            json={"equipment": "Centrifugal pump", "problem": "Low discharge pressure"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"]
    assert payload["next_checks"]


def test_alarm_history_identifies_recurring_issues() -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with TestClient(app) as client:
        response = client.post("/api/alarms/bulk", json=[
            {"equipment": "Compressor K-301", "alarm_code": "VIB_HIGH", "message": "High vibration", "occurred_at": timestamp},
            {"equipment": "Compressor K-301", "alarm_code": "VIB_HIGH", "message": "High vibration again", "occurred_at": timestamp},
        ])
        recurring = client.get("/api/alarms/recurring").json()

    assert response.status_code == 201
    assert recurring[0]["alarm_code"] == "VIB_HIGH"
    assert recurring[0]["occurrences"] >= 2


def test_write_auth_is_optional_for_local_development() -> None:
    os.environ.pop("API_ACCESS_TOKEN", None)
    with TestClient(app) as client:
        response = client.post("/api/documents", json={
            "title": "Local test procedure",
            "equipment": "Test valve",
            "content": "Use this procedure only for local API authentication testing.",
        })

    assert response.status_code == 201
