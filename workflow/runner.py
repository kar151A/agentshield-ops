"""Small helpers to start a workflow, see what it is waiting for, and resume it."""
from typing import Optional

from langgraph.types import Command


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def start_workflow(graph, raw_alert: dict, thread_id: str) -> dict:
    graph.invoke({"raw_alert": raw_alert}, _config(thread_id))
    return graph.get_state(_config(thread_id)).values


def pending_approval(graph, thread_id: str) -> Optional[dict]:
    """The payload an approver must review, or None if nothing is waiting."""
    snapshot = graph.get_state(_config(thread_id))
    if not snapshot.next:
        return None
    for task in snapshot.tasks:
        for item in task.interrupts:
            return item.value
    return None


def submit_decision(graph, thread_id: str, approved: bool, approver: str,
                    action_hash: Optional[str] = None) -> dict:
    """Resume a paused workflow. action_hash must match the proposed action."""
    if action_hash is None:
        action_hash = (pending_approval(graph, thread_id) or {}).get("action_hash")
    decision = {"approved": approved, "approver": approver, "action_hash": action_hash}
    graph.invoke(Command(resume=decision), _config(thread_id))
    return graph.get_state(_config(thread_id)).values
