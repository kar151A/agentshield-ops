"""
Run the full workflow (stubs) for one alert.

    python run_workflow.py --scenario deployment_failure                    # runs until the approval pause
    python run_workflow.py --scenario deployment_failure --decision approve
    python run_workflow.py --scenario suspicious_traffic --decision reject
    python run_workflow.py --scenario deployment_failure --decision tamper  # approval for the WRONG action

NOTE: the checkpointer is in-memory, so the pause and the resume happen inside
this one process. A Postgres checkpointer (Day 14) lets them be separate runs.
"""
import argparse
import json
from pathlib import Path

from clients.mock_backend import MockIngestionClient
from generator.mock_alerts import SCENARIOS, generate_alert
from workflow.graph import build_workflow
from workflow.runner import pending_approval, start_workflow, submit_decision


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", choices=SCENARIOS, default="deployment_failure")
    p.add_argument("--run-id", default="demo-1")
    p.add_argument("--api-key", default="key-org-a")
    p.add_argument("--backend-file", default=".mock_backend.json")
    p.add_argument("--decision", choices=["none", "approve", "reject", "tamper"], default="none")
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()

    if args.reset:
        Path(args.backend_file).unlink(missing_ok=True)
        print("mock backend cleared")
        return

    graph = build_workflow(MockIngestionClient(args.backend_file, args.api_key))
    thread_id = f"wf:{args.scenario}:{args.run_id}"   # TODO: prefix with org once known

    state = start_workflow(graph, generate_alert(args.scenario, args.run_id), thread_id)
    waiting = pending_approval(graph, thread_id)

    if waiting:
        print("PAUSED - waiting for a human approver")
        print(json.dumps({"incident": waiting["incident_id"], "action": waiting["action"],
                          "risk": waiting["policy"]["risk_score"],
                          "warnings": waiting["simulation"]["warnings"]}, indent=2))
        if args.decision != "none":
            wrong = "0000000000000000" if args.decision == "tamper" else None
            state = submit_decision(graph, thread_id, approved=args.decision != "reject",
                                    approver="demo-approver", action_hash=wrong)
            print(f"\nRESUMED with decision: {args.decision}")

    print("\nsteps run :", " -> ".join(state.get("trail", [])))
    print("status    :", state.get("status"))
    if state.get("error"):
        print("error     :", state["error"])
    if state.get("execution"):
        print("executed  :", state["execution"]["adapter"], state["execution"]["outcome"])
    if state.get("approval") and state["approval"].get("reason"):
        print("reason    :", state["approval"]["reason"])


if __name__ == "__main__":
    main()
