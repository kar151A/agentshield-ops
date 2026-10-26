"""
Workflow steps. Every node here is a STUB returning fixed fake data, except
the safety logic (approval gate + execute guard), which is real.
Each stub says which later stage replaces it.
"""
import hashlib
import json

from langgraph.types import interrupt


def action_hash(action: dict) -> str:
    """Fingerprint of the exact action. Approval is bound to this value, so
    changing the action after approval invalidates the approval."""
    body = {k: v for k, v in action.items() if k not in ("action_hash", "state")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- sanitize
def sanitize(state: dict) -> dict:
    # STUB (Day 10): real prompt-injection / secret / mismatched-target checks.
    event = state["event"]
    return {
        "evidence": [{"id": "ev-1", "kind": "alert", "data": event["evidence"]}],
        "status": "investigating",
        "trail": ["sanitize"],
    }


# ------------------------------------------------------------- investigate
def investigate_deployment(state: dict) -> dict:
    # STUB (Day 9 tools + Day 11 Deep Agent). Fixed evidence, read-only.
    evidence = state["evidence"] + [
        {"id": "ev-2", "kind": "log", "data": "CrashLoopBackOff: payments-api restarted 6 times"},
        {"id": "ev-3", "kind": "metric", "data": "error rate 12% (baseline 0.5%)"},
        {"id": "ev-4", "kind": "deployment_history",
         "data": "new revision rolled out 4 minutes before the first alert"},
    ]
    root_cause = {
        "hypothesis": "The newest deployment revision introduced the crash loop",
        "confidence": 0.9,  # fake
        "evidence_ids": ["ev-2", "ev-3", "ev-4"],
    }
    return {"evidence": evidence, "root_cause": root_cause, "trail": ["investigate_deployment"]}


def investigate_traffic(state: dict) -> dict:
    # STUB (Day 9 tools + Day 11 Deep Agent).
    ip = state["event"]["evidence"].get("source_ip", "unknown")
    evidence = state["evidence"] + [
        {"id": "ev-2", "kind": "request_pattern", "data": f"burst of requests to /login from {ip}"},
        {"id": "ev-3", "kind": "baseline", "data": "normal rate for this endpoint is far lower"},
    ]
    root_cause = {
        "hypothesis": f"Automated abuse of the login endpoint from {ip}",
        "confidence": 0.8,  # fake
        "evidence_ids": ["ev-2", "ev-3"],
    }
    return {"evidence": evidence, "root_cause": root_cause, "trail": ["investigate_traffic"]}


# ----------------------------------------------------------------- propose
def propose(state: dict) -> dict:
    # STUB (Day 11): the real agent proposes; here a fixed rule does.
    event = state["event"]
    if event["incident_type"] == "deployment_failure":
        previous = event["evidence"].get("previous_revision") or "previous"
        action = {"kind": "rollback", "target": event["service"], "to_revision": previous}
    else:
        action = {"kind": "block_ip", "target": event["evidence"].get("source_ip"),
                  "duration_minutes": 30}
    action["state"] = "proposed"          # NOT executed
    action["action_hash"] = action_hash(action)
    return {"proposed_action": action, "trail": ["propose"]}


# ---------------------------------------------------------------- simulate
def simulate(state: dict) -> dict:
    # STUB (Day 13): real dry-run adapters.
    action = state["proposed_action"]
    if action["kind"] == "rollback":
        sim = {"predicted_effect": f"service returns to revision {action['to_revision']}",
               "affected_resources": [f"deployment/{action['target']}"],
               "warnings": [], "risk_score": 40}
    else:
        sim = {"predicted_effect": f"requests from {action['target']} are dropped",
               "affected_resources": [f"ip/{action['target']}"],
               "warnings": ["legitimate users may share this IP"], "risk_score": 25}
    sim["action_hash"] = action["action_hash"]
    return {"simulation": sim, "trail": ["simulate"]}


# ------------------------------------------------------------ policy check
def policy_check(state: dict) -> dict:
    # STUB (Karthik, Days 8/17): deterministic policy engine decides, never the LLM.
    policy = {"decision": "REQUIRE_APPROVAL", "policy_id": "stub-policy", "policy_version": "0",
              "risk_score": state["simulation"]["risk_score"],
              "explanation": "STUB: every action requires human approval"}
    status = "action_denied" if policy["decision"] == "DENY" else "awaiting_approval"
    return {"policy": policy, "status": status, "trail": ["policy_check"]}


# ----------------------------------------------------------- approval gate
def approval_gate(state: dict) -> dict:
    """Pauses the graph until a human decision is supplied.

    IMPORTANT: when the graph resumes, this node runs again FROM THE TOP, and
    interrupt() then returns the human's answer. So nothing with side effects
    may sit above the interrupt() call.
    """
    action = state["proposed_action"]
    decision = interrupt({
        "incident_id": state["result"]["incident_id"],
        "action": action,
        "action_hash": action["action_hash"],
        "simulation": state["simulation"],
        "policy": state["policy"],
    })

    if not decision.get("approved"):
        reason = "rejected_by_approver"
    elif decision.get("action_hash") != action["action_hash"]:
        reason = "action_hash_mismatch"   # approval was for a different action
    else:
        reason = None

    approval = {"approved": reason is None, "approver": decision.get("approver"),
                "action_hash": decision.get("action_hash"), "reason": reason}
    return {"approval": approval,
            "status": "approved" if reason is None else "action_rejected",
            "trail": ["approval_gate"]}


# ----------------------------------------------------------------- execute
def execute(state: dict) -> dict:
    """Runs the action through a MOCK adapter. Refuses without a valid approval
    for this exact action - a second line of defence behind the graph routing."""
    approval = state.get("approval", {})
    action = state["proposed_action"]
    if not approval.get("approved") or approval.get("action_hash") != action["action_hash"]:
        raise PermissionError("execution requires a valid approval for this exact action")
    execution = {"adapter": "mock", "action_hash": action["action_hash"],
                 "idempotency_key": f"{state['result']['incident_id']}:{action['action_hash']}",
                 "outcome": "success"}
    return {"execution": execution, "status": "executed", "trail": ["execute"]}


# ------------------------------------------------------------------ verify
def verify(state: dict) -> dict:
    # STUB (Day 16): real before/after health comparison.
    recovered = True
    return {"verification": {"recovered": recovered, "checks": ["stub health check"]},
            "status": "resolved" if recovered else "escalated",
            "trail": ["verify"]}
