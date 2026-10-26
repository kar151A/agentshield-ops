"""
One command: generate a raw alert, run the detection agent, ingest it.

    python run_detection.py --scenario deployment_failure
    python run_detection.py --scenario suspicious_traffic
    python run_detection.py --scenario malformed
    python run_detection.py --scenario deployment_failure --run-id demo-2   # a NEW event
    python run_detection.py --reset                                          # clear mock backend
"""
import argparse
import json
from pathlib import Path

from clients.mock_backend import MockIngestionClient
from detection.agent import build_detection_graph
from generator.mock_alerts import SCENARIOS, generate_alert


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS, default="deployment_failure")
    parser.add_argument("--run-id", default="demo-1", help="same run-id = same event = same idempotency key")
    parser.add_argument("--api-key", default="key-org-a")
    parser.add_argument("--backend-file", default=".mock_backend.json")
    parser.add_argument("--show-raw", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if args.reset:
        Path(args.backend_file).unlink(missing_ok=True)
        print("mock backend cleared")
        return

    raw = generate_alert(args.scenario, args.run_id)
    if args.show_raw:
        print("RAW ALERT:\n" + json.dumps(raw, indent=2) + "\n")

    client = MockIngestionClient(args.backend_file, args.api_key)
    out = build_detection_graph(client).invoke({"raw_alert": raw})

    print(f"status : {out['status']}")
    if out.get("error"):
        print(f"error  : {out['error']}")
    if out.get("result"):
        r = out["result"]
        print(f"incident_id: {r['incident_id']}  org: {r['org_id']}  created: {r['created']}")
        print(f"idempotency_key: {out['event']['idempotency_key']}")
    if out.get("event"):
        e = out["event"]
        print(f"normalized: type={e['incident_type']} severity={e['severity']} "
              f"service={e['service']} env={e['environment']}")


if __name__ == "__main__":
    main()
