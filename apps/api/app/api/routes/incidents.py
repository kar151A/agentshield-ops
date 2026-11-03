from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from app.core.security import TenantContext, get_tenant_context
from app.repositories.incident_repository import incident_repository
from app.schemas.incident import IncidentCreate, IncidentResponse


router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
)


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "model": IncidentResponse,
            "description": (
                "The request was already processed; "
                "the existing incident is returned."
            ),
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid API key.",
        },
        status.HTTP_403_FORBIDDEN: {
            "description": (
                "The API key is not authorized for the organization."
            ),
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The incident payload or headers are invalid.",
        },
    },
    summary="Ingest an operational incident",
)
def create_incident(
    incident: IncidentCreate,
    response: Response,
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
        ),
    ],
) -> IncidentResponse:
    stored_incident, created = incident_repository.create_or_get(
        incident=incident,
        organization_id=tenant.organization_id,
        idempotency_key=idempotency_key,
    )

    if not created:
        response.status_code = status.HTTP_200_OK

    return stored_incident