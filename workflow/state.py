"""
Shared state that flows through the full incident workflow.

Status values (WorkflowState.status), in the order a successful run sees them:
  ingested -> investigating -> awaiting_approval -> approved -> executed -> resolved

Early exits / hand-offs to a human:
  rejected         alert failed validation (nothing stored)
  duplicate        alert already ingested (no second investigation)
  failed           backend refused the request
  action_denied    policy said DENY
  action_rejected  human rejected, or approval did not match the exact action
  escalated        executed, but recovery was NOT verified -> human takes over
"""
import operator
from typing import Annotated, Optional, TypedDict


class WorkflowState(TypedDict, total=False):
    # --- from the Stage 1 detection agent ---
    raw_alert: dict
    event: dict      # normalized IncidentEvent
    result: dict     # ingestion result: incident_id, org_id, created
    error: Optional[str]
    status: str

    # --- investigation ---
    evidence: list[dict]
    root_cause: dict

    # --- action lifecycle: proposed -> simulated -> approved -> executed -> verified ---
    # "proposed" and "executed" live in separate fields on purpose, so a
    # proposal can never be mistaken for something that actually ran.
    proposed_action: dict
    simulation: dict
    policy: dict
    approval: dict
    execution: dict
    verification: dict

    # Ordered list of steps that have run. The reducer APPENDS instead of
    # overwriting, so every node can add its own entry.
    trail: Annotated[list[str], operator.add]
