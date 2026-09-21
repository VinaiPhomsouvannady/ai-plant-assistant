from fastapi.testclient import TestClient

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
