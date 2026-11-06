from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.schemas.incident import IncidentCreate


VALID_INCIDENT = {
    "incident_type": "deployment_failure",
    "severity": "high",
    "title": "payments-api pods failing after deployment",
    "service": "payments-api",
    "environment": "development",
    "source": "mock_kubernetes_alert_generator",
    "source_event_id": "alert-20261103-001",
    "detected_at": "2026-11-03T04:00:00Z",
    "evidence": {
        "healthy_replicas": 0,
        "expected_replicas": 3,
        "error_rate_percent": 38.5,
        "suspected_deployment": "payments-api-v2",
    },
    "status": "open",
}


def test_valid_incident_is_accepted() -> None:
    incident = IncidentCreate.model_validate(VALID_INCIDENT)

    assert incident.service == "payments-api"
    assert incident.incident_type.value == "deployment_failure"
    assert incident.detected_at.tzinfo is not None


def test_unknown_fields_are_rejected() -> None:
    payload = deepcopy(VALID_INCIDENT)
    payload["execute_immediately"] = True

    with pytest.raises(ValidationError):
        IncidentCreate.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("incident_type", "unknown_incident"),
        ("severity", "urgent"),
        ("environment", "customer-production"),
        ("service", "Payments API"),
    ],
)
def test_invalid_controlled_values_are_rejected(
    field: str,
    invalid_value: str,
) -> None:
    payload = deepcopy(VALID_INCIDENT)
    payload[field] = invalid_value

    with pytest.raises(ValidationError):
        IncidentCreate.model_validate(payload)


def test_timestamp_without_timezone_is_rejected() -> None:
    payload = deepcopy(VALID_INCIDENT)
    payload["detected_at"] = "2026-11-03T04:00:00"

    with pytest.raises(
        ValidationError,
        match="detected_at must include timezone information",
    ):
        IncidentCreate.model_validate(payload)
