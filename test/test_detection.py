import json

import pytest

from clients.mock_backend import MockIngestionClient
from detection.agent import build_detection_graph
from detection.normalize import normalize_alert, normalize_severity
from generator.mock_alerts import generate_alert


@pytest.fixture
def backend_file(tmp_path):
    return str(tmp_path / "backend.json")


def run(raw, backend_file, api_key="key-org-a"):
    client = MockIngestionClient(backend_file, api_key)
    return build_detection_graph(client).invoke({"raw_alert": raw}), client


# ---------- normalization ----------

def test_deployment_failure_is_normalized():
    e = normalize_alert(generate_alert("deployment_failure"))
    assert e.incident_type == "deployment_failure"
    assert e.severity == "high"            # "High" -> "high"
    assert e.service == "payments-api"
    assert e.environment == "development"  # "dev" -> "development"
    assert e.evidence["previous_revision"] == "41"


def test_suspicious_traffic_is_normalized():
    e = normalize_alert(generate_alert("suspicious_traffic"))
    assert e.incident_type == "suspicious_traffic"
    assert e.severity == "medium"          # "med" -> "medium"
    assert e.evidence["source_ip"] == "203.0.113.45"
    assert e.evidence["window_seconds"] == 60


@pytest.mark.parametrize("raw,expected", [
    ("HIGH", "high"), (" crit ", "critical"), ("Warn", "medium"), ("info", "low"),
])
def test_severity_variants(raw, expected):
    assert normalize_severity(raw) == expected


def test_same_event_gives_same_idempotency_key():
    a = normalize_alert(generate_alert("deployment_failure", "demo-1"))
    b = normalize_alert(generate_alert("deployment_failure", "demo-1"))
    c = normalize_alert(generate_alert("deployment_failure", "demo-2"))
    assert a.idempotency_key == b.idempotency_key
    assert a.idempotency_key != c.idempotency_key


def test_free_text_is_length_capped():
    raw = generate_alert("deployment_failure")
    raw["annotations"]["restarts"] = "x" * 5000
    assert len(normalize_alert(raw).evidence["restarts"]) == 500


# ---------- rejection ----------

def test_malformed_alert_is_rejected_and_not_stored(backend_file):
    out, client = run(generate_alert("malformed"), backend_file)
    assert out["status"] == "rejected"
    assert "severity" in out["error"]
    assert client.count("org-a") == 0


@pytest.mark.parametrize("mutate", [
    lambda a: a["labels"].pop("deployment"),
    lambda a: a.pop("startsAt"),
    lambda a: a["labels"].update(env="moon"),
])
def test_missing_or_bad_fields_are_rejected(mutate, backend_file):
    raw = generate_alert("deployment_failure")
    mutate(raw)
    out, _ = run(raw, backend_file)
    assert out["status"] == "rejected"


def test_bad_ip_is_rejected(backend_file):
    raw = generate_alert("suspicious_traffic")
    raw["src_ip"] = "999.1.1.1"
    out, _ = run(raw, backend_file)
    assert out["status"] == "rejected"


def test_unknown_shape_is_rejected(backend_file):
    out, _ = run({"hello": "world"}, backend_file)
    assert out["status"] == "rejected"


# ---------- ingestion + idempotency (the Day 5 requirement) ----------

@pytest.mark.parametrize("scenario", ["deployment_failure", "suspicious_traffic"])
def test_creates_exactly_one_incident_and_repeat_creates_no_duplicate(scenario, backend_file):
    raw = generate_alert(scenario)
    first, client = run(raw, backend_file)
    second, _ = run(raw, backend_file)

    assert first["status"] == "ingested"
    assert first["result"]["created"] is True
    assert second["status"] == "duplicate"
    assert second["result"]["created"] is False
    assert second["result"]["incident_id"] == first["result"]["incident_id"]
    assert client.count("org-a") == 1


def test_new_event_creates_a_new_incident(backend_file):
    run(generate_alert("deployment_failure", "demo-1"), backend_file)
    _, client = run(generate_alert("deployment_failure", "demo-2"), backend_file)
    assert client.count("org-a") == 2


def test_incident_goes_to_the_correct_tenant(backend_file):
    raw = generate_alert("deployment_failure")
    a, client_a = run(raw, backend_file, "key-org-a")
    b, _ = run(raw, backend_file, "key-org-b")
    assert a["result"]["org_id"] == "org-a"
    assert b["result"]["org_id"] == "org-b"
    assert b["status"] == "ingested"                 # same key, different tenant: not a duplicate
    assert a["result"]["incident_id"] != b["result"]["incident_id"]
    assert client_a.count("org-a") == 1 and client_a.count("org-b") == 1


def test_invalid_api_key_is_refused(backend_file):
    out, client = run(generate_alert("deployment_failure"), backend_file, "wrong-key")
    assert out["status"] == "failed"
    assert "API key" in out["error"]
    assert client.count("org-a") == 0


def test_same_key_with_different_payload_is_refused(backend_file):
    raw = generate_alert("deployment_failure")
    run(raw, backend_file)
    tampered = json.loads(json.dumps(raw))
    tampered["labels"]["severity"] = "low"           # same fingerprint, different content
    out, client = run(tampered, backend_file)
    assert out["status"] == "failed"
    assert client.count("org-a") == 1
