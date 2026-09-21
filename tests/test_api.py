from fastapi.testclient import TestClient
from datetime import datetime, timezone

from backend.app import app


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
