from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


EvidenceValue = str | int | float | bool


class IncidentType(StrEnum):
    DEPLOYMENT_FAILURE = "deployment_failure"
    SUSPICIOUS_TRAFFIC = "suspicious_traffic"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentEnvironment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class IncidentCreate(BaseModel):
    """Validated incident accepted by the ingestion API."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    incident_type: IncidentType
    severity: IncidentSeverity
    title: str = Field(min_length=5, max_length=200)
    service: str = Field(
        min_length=2,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
    )
    environment: IncidentEnvironment
    source: str = Field(min_length=2, max_length=100)
    source_event_id: str = Field(min_length=3, max_length=128)
    detected_at: datetime
    evidence: dict[str, EvidenceValue] = Field(default_factory=dict)
    status: Literal["open"] = "open"

    @field_validator("detected_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject ambiguous timestamps without timezone information."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("detected_at must include timezone information")

        return value


class IncidentResponse(IncidentCreate):
    """Incident returned after successful ingestion."""

    incident_id: UUID
    organization_id: str
    created_at: datetime