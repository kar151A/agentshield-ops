from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.incident import IncidentModel
from app.schemas.incident import IncidentCreate, IncidentResponse


class PostgresIncidentRepository:
    def create_or_get(
        self,
        database_session: Session,
        incident: IncidentCreate,
        organization_id: str,
        idempotency_key: str,
    ) -> tuple[IncidentResponse, bool]:
        existing_incident = self._find_by_idempotency_key(
            database_session=database_session,
            organization_id=organization_id,
            idempotency_key=idempotency_key,
        )

        if existing_incident is not None:
            return self._to_response(existing_incident), False

        incident_model = IncidentModel(
            organization_id=organization_id,
            idempotency_key=idempotency_key,
            incident_type=incident.incident_type.value,
            severity=incident.severity.value,
            title=incident.title,
            service=incident.service,
            environment=incident.environment.value,
            source=incident.source,
            source_event_id=incident.source_event_id,
            detected_at=incident.detected_at.astimezone(UTC),
            evidence=incident.evidence,
            status=incident.status,
        )

        database_session.add(incident_model)

        try:
            database_session.commit()
        except IntegrityError:
            database_session.rollback()

            existing_incident = self._find_by_idempotency_key(
                database_session=database_session,
                organization_id=organization_id,
                idempotency_key=idempotency_key,
            )

            if existing_incident is None:
                raise

            return self._to_response(existing_incident), False

        database_session.refresh(incident_model)

        return self._to_response(incident_model), True

    def _find_by_idempotency_key(
        self,
        database_session: Session,
        organization_id: str,
        idempotency_key: str,
    ) -> IncidentModel | None:
        statement = select(IncidentModel).where(
            IncidentModel.organization_id == organization_id,
            IncidentModel.idempotency_key == idempotency_key,
        )

        return database_session.scalar(statement)

    def _ensure_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    def _to_response(
        self,
        incident: IncidentModel,
    ) -> IncidentResponse:
        return IncidentResponse(
            incident_id=incident.incident_id,
            organization_id=incident.organization_id,
            incident_type=incident.incident_type,
            severity=incident.severity,
            title=incident.title,
            service=incident.service,
            environment=incident.environment,
            source=incident.source,
            source_event_id=incident.source_event_id,
            detected_at=self._ensure_utc(incident.detected_at),
            evidence=incident.evidence,
            status=incident.status,
            created_at=self._ensure_utc(incident.created_at),
        )


postgres_incident_repository = PostgresIncidentRepository()