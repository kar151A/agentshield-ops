"""
Deterministic normalization: raw alert -> IncidentEvent.
Raises ValueError (incl. pydantic ValidationError) on anything invalid.
No LLM involved.
"""
import hashlib
import ipaddress
import re
from datetime import datetime, timezone

from contracts.incident import IncidentEvent

SEVERITY_MAP = {
    "low": "low", "info": "low", "minor": "low",
    "medium": "medium", "med": "medium", "warn": "medium", "warning": "medium",
    "high": "high", "major": "high",
    "critical": "critical", "crit": "critical", "severe": "critical",
}
ENV_MAP = {
    "dev": "development", "development": "development",
    "stage": "staging", "staging": "staging",
    "prod": "production", "production": "production",
}
MAX_TEXT = 500  # cap on free text copied into evidence (untrusted input)


def _require(data: dict, key: str):
    if key not in data or data[key] in (None, ""):
        raise ValueError(f"missing field: {key}")
    return data[key]


def _clean_text(value, limit: int = MAX_TEXT) -> str:
    return str(value).strip()[:limit]


def normalize_severity(value) -> str:
    key = str(value).strip().lower()
    if key not in SEVERITY_MAP:
        raise ValueError(f"unknown severity: {value!r}")
    return SEVERITY_MAP[key]


def normalize_environment(value) -> str:
    key = str(value).strip().lower()
    if key not in ENV_MAP:
        raise ValueError(f"unknown environment: {value!r}")
    return ENV_MAP[key]


def parse_timestamp(value) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def make_idempotency_key(source: str, source_event_id: str) -> str:
    """Same source event -> same key. The backend scopes keys per tenant."""
    return hashlib.sha256(f"{source}:{source_event_id}".encode()).hexdigest()[:32]


def _parse_window_seconds(value) -> int:
    match = re.fullmatch(r"(\d+)\s*([sm])", str(value).strip().lower())
    if not match:
        raise ValueError(f"bad window: {value!r}")
    amount, unit = int(match.group(1)), match.group(2)
    return amount * (60 if unit == "m" else 1)


def normalize_k8s_alert(raw: dict) -> IncidentEvent:
    labels = raw.get("labels") or {}
    annotations = raw.get("annotations") or {}
    service = labels.get("deployment") or labels.get("service")
    if not service:
        raise ValueError("missing field: labels.deployment")
    fingerprint = str(_require(raw, "fingerprint"))
    return IncidentEvent(
        idempotency_key=make_idempotency_key("alertmanager", fingerprint),
        incident_type="deployment_failure",
        severity=normalize_severity(_require(labels, "severity")),
        title=_clean_text(annotations.get("summary") or raw.get("alertname"), 200),
        service=_clean_text(service, 100),
        environment=normalize_environment(_require(labels, "env")),
        source="alertmanager",
        source_event_id=fingerprint,
        detected_at=parse_timestamp(_require(raw, "startsAt")),
        evidence={
            "alertname": _clean_text(raw.get("alertname", "")),
            "restarts": _clean_text(annotations.get("restarts", "")),
            "deployment_revision": _clean_text(annotations.get("deployment_revision", "")),
            "previous_revision": _clean_text(annotations.get("previous_revision", "")),
            "namespace": _clean_text(labels.get("namespace", "")),
            "cluster": _clean_text(labels.get("cluster", "")),
        },
    )


def normalize_traffic_alert(raw: dict) -> IncidentEvent:
    ip = str(ipaddress.ip_address(str(_require(raw, "src_ip")).strip()))  # ValueError if bad
    hits = int(_require(raw, "hits"))
    if hits < 0:
        raise ValueError("hits must not be negative")
    service = _clean_text(_require(raw, "service"), 100)
    event_id = str(_require(raw, "id"))
    return IncidentEvent(
        idempotency_key=make_idempotency_key("waf", event_id),
        incident_type="suspicious_traffic",
        severity=normalize_severity(_require(raw, "sev")),
        title=f"Suspicious traffic from {ip} to {service}",
        service=service,
        environment=normalize_environment(_require(raw, "env")),
        source="waf",
        source_event_id=event_id,
        detected_at=parse_timestamp(_require(raw, "ts")),
        evidence={
            "source_ip": ip,
            "request_count": hits,
            "window_seconds": _parse_window_seconds(_require(raw, "window")),
            "target_path": _clean_text(raw.get("path", "")),
            "rule": _clean_text(raw.get("rule", "")),
        },
    )


def normalize_alert(raw: dict) -> IncidentEvent:
    if not isinstance(raw, dict):
        raise ValueError("alert must be a JSON object")
    if "alertname" in raw:
        return normalize_k8s_alert(raw)
    if "rule" in raw and "src_ip" in raw:
        return normalize_traffic_alert(raw)
    raise ValueError("unrecognized alert shape")
