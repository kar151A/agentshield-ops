import pytest

from clients.mock_backend import MockIngestionClient
from generator.mock_alerts import generate_alert
from workflow import nodes
from workflow.graph import build_workflow
from workflow.runner import pending_approval, start_workflow, submit_decision

FULL_TRAIL = {
    "deployment_failure": ["detect", "sanitize", "investigate_deployment", "propose",
                           "simulate", "policy_check", "approval_gate", "execute", "verify"],
    "suspicious_traffic": ["detect", "sanitize", "investigate_traffic", "propose",
                           "simulate", "policy_check", "approval_gate", "execute", "verify"],
}


class CountingClient(MockIngestionClient):
    """Counts backend calls so we can prove detect is not re-run on resume."""
    calls = 0

    def submit(self, event):
        CountingClient.calls += 1
        return super().submit(event)


@pytest.fixture
def client(tmp_path):
    CountingClient.calls = 0
    return CountingClient(str(tmp_path / "backend.json"), "key-org-a")


@pytest.fixture
def graph(client):
    return build_workflow(client)


# ---------- happy paths, both scenarios, same graph ----------

@pytest.mark.parametrize("scenario,kind", [("deployment_failure", "rollback"),
                                           ("suspicious_traffic", "block_ip")])
def test_full_run_after_approval(graph, scenario, kind):
    state = start_workflow(graph, generate_alert(scenario), "t1")
    assert state["status"] == "awaiting_approval"
    assert state["proposed_action"]["kind"] == kind

    state = submit_decision(graph, "t1", approved=True, approver="alice")
    assert state["trail"] == FULL_TRAIL[scenario]
    assert state["status"] == "resolved"
    assert state["execution"]["outcome"] == "success"
    assert state["verification"]["recovered"] is True


# ---------- the pause ----------

def test_pauses_before_execute_and_exposes_what_to_review(graph):
    state = start_workflow(graph, generate_alert("deployment_failure"), "t1")
    waiting = pending_approval(graph, "t1")
    assert waiting["action"]["kind"] == "rollback"
    assert waiting["action"]["state"] == "proposed"     # proposed, not executed
    assert waiting["action_hash"] == state["proposed_action"]["action_hash"]
    assert "execution" not in state                      # nothing ran yet
    assert state["trail"][-1] == "policy_check"


def test_nothing_pending_for_a_finished_workflow(graph):
    start_workflow(graph, generate_alert("deployment_failure"), "t1")
    submit_decision(graph, "t1", approved=True, approver="alice")
    assert pending_approval(graph, "t1") is None


# ---------- resume does not repeat earlier steps (docket Day 14 idea) ----------

def test_resume_does_not_repeat_steps(graph):
    start_workflow(graph, generate_alert("deployment_failure"), "t1")
    assert CountingClient.calls == 1
    state = submit_decision(graph, "t1", approved=True, approver="alice")
    assert CountingClient.calls == 1                     # detect not re-run
    assert len(state["trail"]) == len(set(state["trail"]))   # no step twice


# ---------- approval safety ----------

def test_rejection_stops_without_executing(graph):
    start_workflow(graph, generate_alert("deployment_failure"), "t1")
    state = submit_decision(graph, "t1", approved=False, approver="alice")
    assert state["status"] == "action_rejected"
    assert state["approval"]["reason"] == "rejected_by_approver"
    assert "execution" not in state
    assert "execute" not in state["trail"] and "verify" not in state["trail"]


def test_approval_for_a_different_action_is_refused(graph):
    start_workflow(graph, generate_alert("deployment_failure"), "t1")
    state = submit_decision(graph, "t1", approved=True, approver="alice",
                            action_hash="0000000000000000")
    assert state["status"] == "action_rejected"
    assert state["approval"]["reason"] == "action_hash_mismatch"
    assert "execution" not in state


def test_execute_node_refuses_without_valid_approval():
    action = {"kind": "rollback", "target": "x", "to_revision": "1"}
    action["action_hash"] = nodes.action_hash(action)
    base = {"proposed_action": action, "result": {"incident_id": "inc-1"}}
    with pytest.raises(PermissionError):
        nodes.execute(base)                                              # no approval
    with pytest.raises(PermissionError):
        nodes.execute({**base, "approval": {"approved": False, "action_hash": action["action_hash"]}})
    with pytest.raises(PermissionError):
        nodes.execute({**base, "approval": {"approved": True, "action_hash": "wrong"}})


def test_action_hash_changes_when_action_changes():
    a = {"kind": "block_ip", "target": "203.0.113.45", "duration_minutes": 30}
    b = {**a, "target": "203.0.113.99"}
    assert nodes.action_hash(a) != nodes.action_hash(b)
    assert nodes.action_hash(a) == nodes.action_hash({**a, "state": "proposed"})  # status ignored


# ---------- early exits ----------

def test_malformed_alert_stops_at_detect(graph):
    state = start_workflow(graph, generate_alert("malformed"), "t1")
    assert state["status"] == "rejected"
    assert state["trail"] == ["detect"]
    assert pending_approval(graph, "t1") is None


def test_duplicate_alert_does_not_start_a_second_investigation(graph):
    start_workflow(graph, generate_alert("deployment_failure"), "t1")
    state = start_workflow(graph, generate_alert("deployment_failure"), "t2")   # same alert, new thread
    assert state["status"] == "duplicate"
    assert state["trail"] == ["detect"]
    assert "evidence" not in state


def test_backend_refusal_stops_workflow(tmp_path):
    bad = MockIngestionClient(str(tmp_path / "b.json"), "wrong-key")
    state = start_workflow(build_workflow(bad), generate_alert("deployment_failure"), "t1")
    assert state["status"] == "failed"
    assert state["trail"] == ["detect"]


def test_failed_verification_escalates_to_a_human(client):
    def failing_verify(state):
        return {"verification": {"recovered": False}, "status": "escalated", "trail": ["verify"]}
    graph = build_workflow(client, verify_fn=failing_verify)
    start_workflow(graph, generate_alert("deployment_failure"), "t1")
    state = submit_decision(graph, "t1", approved=True, approver="alice")
    assert state["status"] == "escalated"


# ---------- isolation between workflows ----------

def test_two_workflows_do_not_share_state(graph):
    start_workflow(graph, generate_alert("deployment_failure"), "t1")
    start_workflow(graph, generate_alert("suspicious_traffic"), "t2")
    a, b = pending_approval(graph, "t1"), pending_approval(graph, "t2")
    assert a["action"]["kind"] == "rollback" and b["action"]["kind"] == "block_ip"
    submit_decision(graph, "t1", approved=False, approver="alice")
    assert pending_approval(graph, "t2") is not None      # t2 still waiting
