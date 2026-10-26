from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check_returns_service_status() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "AgentShield Ops API",
        "version": "0.1.0",
        "environment": "development",
    }


def test_unknown_route_returns_not_found() -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404