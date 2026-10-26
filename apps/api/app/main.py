from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Secure control API for AgentShield Ops incident-response workflows."
    ),
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

app.include_router(
    health_router,
    prefix=settings.api_prefix,
)


@app.get("/", tags=["Service"])
def service_information() -> dict[str, str]:
    """Return non-sensitive service metadata."""

    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "documentation": "/docs",
    }