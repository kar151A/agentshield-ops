"""
Shared incident contract (Stage 0).

IncidentEvent  = what the worker SENDS to the ingestion API.
IngestionResult = what the API RETURNS.

NOTE: there is deliberately no org_id in IncidentEvent. The tenant is
derived by the backend from the API key, never from the payload.

OPEN DECISION with Karthik: the incident_type names below.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

IncidentType = Literal["deployment_failure", "suspicious_traffic"]
Severity = Literal["low", "medium", "high", "critical"]
Environment = Literal["development", "staging", "production"]


class IncidentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128)
    incident_type: IncidentType
    severity: Severity
    title: str = Field(min_length=1, max_length=200)
    service: Optional[str] = Field(default=None, max_length=100)
    environment: Environment
    source: str = Field(min_length=1, max_length=50)
    source_event_id: str = Field(min_length=1, max_length=200)
    detected_at: datetime
    evidence: dict = Field(default_factory=dict)
    status: Literal["open"] = "open"


class IngestionResult(BaseModel):
    incident_id: str
    org_id: str
    created: bool  # True = new incident, False = duplicate of an earlier request
    status: str
