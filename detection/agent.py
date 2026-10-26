"""
Incident Detection Agent (Stage 1) - a LangGraph graph, no LLM.

    START -> validate_and_normalize --ok--> submit_to_backend -> END
                       |
                       +--invalid--> END  (status = "rejected")

Later stages make this the first node(s) of the full workflow.
"""
from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from clients.mock_backend import IngestionError
from contracts.incident import IncidentEvent
from detection.normalize import normalize_alert


class DetectionState(TypedDict, total=False):
    raw_alert: dict
    event: dict
    result: dict
    error: Optional[str]
    status: str  # "ingested" | "duplicate" | "rejected" | "failed"


def build_detection_graph(client):
    def validate_and_normalize(state: DetectionState) -> dict:
        try:
            event = normalize_alert(state["raw_alert"])
        except (ValueError, KeyError, TypeError) as exc:  # pydantic errors are ValueErrors
            return {"status": "rejected", "error": str(exc)}
        return {"event": event.model_dump(mode="json")}

    def route(state: DetectionState) -> str:
        return "submit" if "event" in state else "reject"

    def submit_to_backend(state: DetectionState) -> dict:
        try:
            result = client.submit(IncidentEvent(**state["event"]))
        except IngestionError as exc:
            return {"status": "failed", "error": str(exc)}
        return {
            "result": result.model_dump(),
            "status": "ingested" if result.created else "duplicate",
        }

    graph = StateGraph(DetectionState)
    graph.add_node("validate_and_normalize", validate_and_normalize)
    graph.add_node("submit_to_backend", submit_to_backend)
    graph.add_edge(START, "validate_and_normalize")
    graph.add_conditional_edges(
        "validate_and_normalize", route,
        {"submit": "submit_to_backend", "reject": END},
    )
    graph.add_edge("submit_to_backend", END)
    return graph.compile()
