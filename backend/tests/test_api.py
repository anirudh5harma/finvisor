import logging

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint():
    response = client.post(
        "/api/chat",
        json={"message": "Why did my portfolio fall today?", "portfolio_id": "PORTFOLIO_002"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["confidence_score"] > 0.6
    assert data["evaluation"]["score"] >= 70
    assert data["response_metadata"]["token_usage"]["total_tokens"] > 0


def test_classified_news_endpoint():
    response = client.get("/api/news/classified")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert {"sentiment", "scope", "impact_level"}.issubset(data[0])


def test_observability_status_endpoint():
    response = client.get("/api/observability/status")

    assert response.status_code == 200
    data = response.json()
    assert {"langfuse_enabled", "langfuse_configured", "client_initialized"}.issubset(data)


def test_request_logging_is_structured(caplog):
    with caplog.at_level(logging.INFO, logger="financial_advisor.api"):
        response = client.get("/api/health")

    assert response.status_code == 200
    record = next(item for item in caplog.records if getattr(item, "event", None) == "http_request")
    assert record.method == "GET"
    assert record.path == "/api/health"
    assert record.status_code == 200
    assert isinstance(record.duration_ms, float)
