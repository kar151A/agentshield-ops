from datetime import UTC, datetime

from app.repositories.incident_repository import InMemoryIncidentRepository
from app.schemas.incident import IncidentCreate


def build_incident() -> IncidentCreate:
    return IncidentCreate(
        incident_type="deployment_failure",
        severity="high",
        title="Checkout deployment failed",
        service="checkout-api",
        environment="staging",
        source="github-actions",
        source_event_id="deployment-123",
        detected_at=datetime.now(UTC),
        evidence={
            "workflow": "deploy-checkout",
            "attempt": 2,
        },
    )


def test_new_incident_is_created() -> None:
    repository = InMemoryIncidentRepository()

    incident, created = repository.create_or_get(
        incident=build_incident(),
        organization_id="org-one",
        idempotency_key="event-123",
    )

    assert created is True
    assert incident.organization_id == "org-one"
    assert incident.title == "Checkout deployment failed"
    assert incident.incident_id is not None
    assert incident.created_at.tzinfo is not None


def test_same_idempotency_key_returns_existing_incident() -> None:
    repository = InMemoryIncidentRepository()
    incident_data = build_incident()

    first_incident, first_created = repository.create_or_get(
        incident=incident_data,
        organization_id="org-one",
        idempotency_key="event-123",
    )

    second_incident, second_created = repository.create_or_get(
        incident=incident_data,
        organization_id="org-one",
        idempotency_key="event-123",
    )

    assert first_created is True
    assert second_created is False
    assert first_incident.incident_id == second_incident.incident_id
    assert first_incident.created_at == second_incident.created_at


def test_idempotency_key_is_isolated_between_organizations() -> None:
    repository = InMemoryIncidentRepository()
    incident_data = build_incident()

    first_incident, first_created = repository.create_or_get(
        incident=incident_data,
        organization_id="org-one",
        idempotency_key="shared-event-key",
    )

    second_incident, second_created = repository.create_or_get(
        incident=incident_data,
        organization_id="org-two",
        idempotency_key="shared-event-key",
    )

    assert first_created is True
    assert second_created is True
    assert first_incident.incident_id != second_incident.incident_id