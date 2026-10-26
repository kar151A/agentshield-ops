from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings


router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Response returned when the API is available."""

    status: Literal["healthy"]
    service: str
    version: str
    environment: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API health",
)
def health_check() -> HealthResponse:
    """Return basic service health without exposing sensitive data."""

    settings = get_settings()

    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )