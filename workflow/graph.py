"""
The full incident workflow (Stage 2 skeleton).

 START -> detect --ingested--> sanitize --(by type)--> investigate_* -> propose
       -> simulate -> policy_check --not denied--> approval_gate (PAUSES)
       --approved--> execute -> verify -> END
 Any other branch ends early with a status that says why.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from detection.agent import build_detection_graph
from workflow import nodes
from workflow.state import WorkflowState


def route_after_detect(state: dict) -> str:
    # Only a NEW, valid incident continues. rejected / failed / duplicate stop here.
    return "sanitize" if state.get("status") == "ingested" else "stop"


def route_by_type(state: dict) -> str:
    if state["event"]["incident_type"] == "deployment_failure":
        return "investigate_deployment"
    return "investigate_traffic"


def route_after_policy(state: dict) -> str:
    return "stop" if state["policy"]["decision"] == "DENY" else "approval_gate"


def route_after_approval(state: dict) -> str:
    return "execute" if state["approval"]["approved"] else "stop"


def build_workflow(client, checkpointer=None, verify_fn=None):
    """client: ingestion client (mock or real). verify_fn: swappable so tests
    can force a failed verification."""
    detection_graph = build_detection_graph(client)

    def detect(state: dict) -> dict:
        out = detection_graph.invoke({"raw_alert": state["raw_alert"]})
        keep = ("event", "result", "error", "status")
        update = {k: out[k] for k in keep if k in out}
        update["trail"] = ["detect"]
        return update

    g = StateGraph(WorkflowState)
    g.add_node("detect", detect)
    g.add_node("sanitize", nodes.sanitize)
    g.add_node("investigate_deployment", nodes.investigate_deployment)
    g.add_node("investigate_traffic", nodes.investigate_traffic)
    g.add_node("propose", nodes.propose)
    g.add_node("simulate", nodes.simulate)
    g.add_node("policy_check", nodes.policy_check)
    g.add_node("approval_gate", nodes.approval_gate)
    g.add_node("execute", nodes.execute)
    g.add_node("verify", verify_fn or nodes.verify)

    g.add_edge(START, "detect")
    g.add_conditional_edges("detect", route_after_detect, {"sanitize": "sanitize", "stop": END})
    g.add_conditional_edges("sanitize", route_by_type, {
        "investigate_deployment": "investigate_deployment",
        "investigate_traffic": "investigate_traffic"})
    g.add_edge("investigate_deployment", "propose")
    g.add_edge("investigate_traffic", "propose")
    g.add_edge("propose", "simulate")
    g.add_edge("simulate", "policy_check")
    g.add_conditional_edges("policy_check", route_after_policy,
                            {"approval_gate": "approval_gate", "stop": END})
    g.add_conditional_edges("approval_gate", route_after_approval,
                            {"execute": "execute", "stop": END})
    g.add_edge("execute", "verify")
    g.add_edge("verify", END)

    # MemorySaver = in-process only. Swap for a Postgres checkpointer (Day 14)
    # so a paused workflow survives restarts.
    return g.compile(checkpointer=checkpointer or MemorySaver())
