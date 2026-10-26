"""
Client for the REAL ingestion API (not tested yet - needs Karthik's endpoint).
The endpoint path and response shape are placeholders until the OpenAPI
contract is agreed (docket Day 3).
"""
from contracts.incident import IncidentEvent, IngestionResult
from clients.mock_backend import IngestionError, Unauthorized


class HttpIngestionClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        import httpx  # imported here so the mock path works without httpx
        self._http = httpx.Client(base_url=base_url, timeout=timeout)
        self._api_key = api_key

    def submit(self, event: IncidentEvent) -> IngestionResult:
        response = self._http.post(
            "/api/v1/incidents",  # PLACEHOLDER path
            json=event.model_dump(mode="json"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Idempotency-Key": event.idempotency_key,
            },
        )
        if response.status_code in (401, 403):
            raise Unauthorized(f"auth failed ({response.status_code})")
        if response.status_code >= 400:
            raise IngestionError(f"backend error {response.status_code}: {response.text[:200]}")
        body = response.json()
        # Assumption: 201 = created, 200 = duplicate. Confirm with Karthik.
        return IngestionResult(
            incident_id=body["incident_id"], org_id=body["org_id"],
            created=response.status_code == 201, status=body.get("status", "open"),
        )
