import importlib
import os
import sys
import zlib
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


def test_document_upload_accepts_text_file() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("pump_procedure.txt", b"Verify suction pressure before startup. Inspect the strainer and confirm discharge flow is stable.", "text/plain")},
            data={"title": "Uploaded pump procedure", "equipment": "Centrifugal pump", "source": "Uploaded SOP"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Uploaded pump procedure"
    assert payload["equipment"] == "Centrifugal pump"
    assert "suction pressure" in payload["content"].lower()


def test_document_upload_parses_pdf_text() -> None:
    content = b"BT /F1 18 Tf 50 100 Td (Verify suction pressure before startup.) Tj ET"
    compressed = zlib.compress(content)
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        b"4 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(compressed) + compressed + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    pdf_bytes = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes += obj
    xref_start = len(pdf_bytes)
    pdf_bytes += b"xref\n0 6\n0000000000 65535 f \n"
    for offset in offsets:
        pdf_bytes += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf_bytes += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")

    with TestClient(app) as client:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("pump_procedure.pdf", pdf_bytes, "application/pdf")},
            data={"title": "Uploaded pump procedure pdf", "equipment": "Centrifugal pump", "source": "Uploaded PDF"},
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["title"] == "Uploaded pump procedure pdf"
    assert "suction pressure" in payload["content"].lower()
    assert "startup" in payload["content"].lower()
