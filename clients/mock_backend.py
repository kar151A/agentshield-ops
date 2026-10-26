"""
Stand-in for Karthik's ingestion API until it exists.
Behaves like the real one should:
  - API key -> tenant (the tenant is never taken from the payload)
  - idempotency keys are scoped PER TENANT
  - same key + same payload  -> returns the existing incident (no duplicate)
  - same key + different payload -> error (like an HTTP 409/422)
State is kept in a JSON file so separate CLI runs share it.
"""
import json
import uuid
from pathlib import Path
from typing import Optional

from contracts.incident import IncidentEvent, IngestionResult

DEFAULT_API_KEYS = {"key-org-a": "org-a", "key-org-b": "org-b"}


class IngestionError(Exception):
    pass


class Unauthorized(IngestionError):
    pass


class MockIngestionClient:
    def __init__(self, path: str, api_key: str, api_keys: Optional[dict] = None):
        self.path = Path(path)
        self.api_key = api_key
        self.api_keys = api_keys or DEFAULT_API_KEYS

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"incidents": {}}

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def submit(self, event: IncidentEvent) -> IngestionResult:
        org_id = self.api_keys.get(self.api_key)
        if org_id is None:
            raise Unauthorized("invalid API key")

        payload = event.model_dump(mode="json")
        data = self._load()
        tenant_incidents = data["incidents"].setdefault(org_id, {})
        existing = tenant_incidents.get(event.idempotency_key)

        if existing:
            if existing["event"] != payload:
                raise IngestionError("idempotency key reused with a different payload")
            return IngestionResult(
                incident_id=existing["incident_id"], org_id=org_id,
                created=False, status=existing["event"]["status"],
            )

        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        tenant_incidents[event.idempotency_key] = {"incident_id": incident_id, "event": payload}
        self._save(data)
        return IngestionResult(incident_id=incident_id, org_id=org_id, created=True, status="open")

    def count(self, org_id: str) -> int:
        return len(self._load()["incidents"].get(org_id, {}))
