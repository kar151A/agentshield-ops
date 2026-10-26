"""
Mock alert generator. Produces RAW, differently-shaped, slightly messy
alerts, like real monitoring tools would. Output is deterministic for a
given (scenario, run_id) so re-running creates the same idempotency key.
"""
import hashlib

BASE_TIME = "2026-10-26T09:00:00Z"
SCENARIOS = ("deployment_failure", "suspicious_traffic", "malformed")


def _fingerprint(scenario: str, run_id: str) -> str:
    return hashlib.sha1(f"{scenario}:{run_id}".encode()).hexdigest()[:16]


def generate_alert(scenario: str, run_id: str = "demo-1") -> dict:
    fp = _fingerprint(scenario, run_id)

    if scenario == "deployment_failure":
        # Alertmanager-style payload (note the messy casing / extra fields)
        return {
            "alertname": "KubePodCrashLooping",
            "status": "firing",
            "fingerprint": fp,
            "startsAt": BASE_TIME,
            "labels": {
                "severity": "High",
                "deployment": "payments-api",
                "namespace": "payments",
                "cluster": "dev-cluster",
                "env": "dev",
            },
            "annotations": {
                "summary": "payments-api pods crash looping after new rollout",
                "restarts": "6",
                "deployment_revision": "42",
                "previous_revision": "41",
            },
            "generatorURL": "http://prometheus.local/graph?g0.expr=...",
        }

    if scenario == "suspicious_traffic":
        # WAF-style payload with a different shape and abbreviations
        return {
            "id": fp,
            "ts": BASE_TIME,
            "rule": "waf-rate-anomaly",
            "src_ip": "203.0.113.45",  # documentation-range IP (safe to use)
            "hits": 850,
            "window": "60s",
            "service": "payments-api",
            "path": "/login",
            "sev": "med",
            "env": "dev",
        }

    if scenario == "malformed":
        alert = generate_alert("deployment_failure", run_id)
        alert["labels"]["severity"] = "banana"  # not a real severity
        return alert

    raise ValueError(f"unknown scenario: {scenario!r} (choose from {SCENARIOS})")
