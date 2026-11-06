import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.repositories.incident_repository import incident_repository


client = TestClient(app)
settings = get_settings()


@pytest.fixture(autouse=True)
def clear_incident_repository() -> None:
    incident_repository.clear()


def valid_headers() -> dict[str, str]:
    return {
        "X-API-Key": settings.ingestion_api_key.get_secret_value(),
        "X-Organization-ID": settings.ingestion_organization_id,
        "Idempotency-Key": "deployment-event-123",
    }


def valid_incident() -> dict[str, object]:
    return {
        "incident_type": "deployment_failure",
        "severity": "high",
        "title": "Checkout deployment failed",
        "service": "checkout-api",
        "environment": "staging",
        "source": "github-actions",
        "source_event_id": "deployment-123",
        "detected_at": "2026-11-03T05:30:00+00:00",
        "evidence": {
            "workflow": "deploy-checkout",
            "attempt": 2,
        },
    }


def test_authenticated_incident_is_created() -> None:
    response = client.post(
        "/api/v1/incidents",
        headers=valid_headers(),
        json=valid_incident(),
    )

    assert response.status_code == 201

    response_body = response.json()

    assert response_body["organization_id"] == (
        settings.ingestion_organization_id
    )
    assert response_body["title"] == "Checkout deployment failed"
    assert response_body["status"] == "open"
    assert response_body["incident_id"]


def test_repeated_idempotency_key_returns_same_incident() -> None:
    first_response = client.post(
        "/api/v1/incidents",
        headers=valid_headers(),
        json=valid_incident(),
    )

    second_response = client.post(
        "/api/v1/incidents",
        headers=valid_headers(),
        json=valid_incident(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200

    assert (
        first_response.json()["incident_id"]
        == second_response.json()["incident_id"]
    )


def test_missing_api_key_is_rejected() -> None:
    headers = valid_headers()
    del headers["X-API-Key"]

    response = client.post(
        "/api/v1/incidents",
        headers=headers,
        json=valid_incident(),
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_wrong_organization_is_rejected() -> None:
    headers = valid_headers()
    headers["X-Organization-ID"] = "unauthorized-organization"

    response = client.post(
        "/api/v1/incidents",
        headers=headers,
        json=valid_incident(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "API key is not authorized for this organization"
    )