from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.incident import IncidentCreate, IncidentResponse


class InMemoryIncidentRepository:
    def __init__(self) -> None:
        self._incidents: dict[str, IncidentResponse] = {}
        self._idempotency_index: dict[tuple[str, str], str] = {}

    def create_or_get(
        self,
        incident: IncidentCreate,
        organization_id: str,
        idempotency_key: str,
    ) -> tuple[IncidentResponse, bool]:
        index_key = (organization_id, idempotency_key)

        existing_incident_id = self._idempotency_index.get(index_key)

        if existing_incident_id is not None:
            existing_incident = self._incidents[existing_incident_id]
            return existing_incident.model_copy(deep=True), False

        incident_response = IncidentResponse(
            **incident.model_dump(),
            incident_id=uuid4(),
            organization_id=organization_id,
            created_at=datetime.now(UTC),
        )

        incident_id = str(incident_response.incident_id)

        self._incidents[incident_id] = incident_response
        self._idempotency_index[index_key] = incident_id

        return incident_response.model_copy(deep=True), True

    def clear(self) -> None:
        self._incidents.clear()
        self._idempotency_index.clear()


incident_repository = InMemoryIncidentRepository()