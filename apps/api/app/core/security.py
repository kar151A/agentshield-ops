from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings


class TenantContext(BaseModel):
    """Trusted tenant identity produced after credential validation."""

    organization_id: str
    authentication_method: str = "api_key"


def get_tenant_context(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[
        str | None,
        Header(alias="X-API-Key"),
    ] = None,
    x_organization_id: Annotated[
        str | None,
        Header(alias="X-Organization-ID"),
    ] = None,
) -> TenantContext:
    """Authenticate an ingestion request and resolve its tenant."""

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    expected_key = settings.ingestion_api_key.get_secret_value()

    if not compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing organization identifier",
        )

    if not compare_digest(
        x_organization_id,
        settings.ingestion_organization_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is not authorized for this organization",
        )

    return TenantContext(
        organization_id=settings.ingestion_organization_id,
    )