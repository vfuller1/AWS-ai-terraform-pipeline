from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from agents.audit_agent import audit_agent
from agents.delete_intake_agent import delete_intake_agent
from agents.destroy_agent import destroy_agent
from agents.impact_agent import impact_agent
from agents.state import DeleteState

load_dotenv()


def await_gates(state: DeleteState) -> DeleteState:
    print("[await_gates] Evaluating gate 3 and gate 4")
    next_state: DeleteState = dict(state)

    if not os.getenv("GITHUB_ACTIONS"):
        # Local development mode auto-passes gate 3 and gate 4.
        next_state["gate3_passed"] = True
        next_state["gate4_passed"] = True
    else:
        next_state["gate3_passed"] = bool(next_state.get("gate3_passed", False))
        next_state["gate4_passed"] = bool(next_state.get("gate4_passed", False))

    return next_state


def _route_impact(state: DeleteState) -> str:
    return END if state.get("dependency_status") == "block" else "await_gates"


def _route_gates(state: DeleteState) -> str:
    if state.get("gate3_passed") and state.get("gate4_passed"):
        return "destroy_agent"
    return END


def build_graph() -> StateGraph:
    graph = StateGraph(DeleteState)

    graph.add_node("delete_intake_agent", delete_intake_agent)
    graph.add_node("impact_agent", impact_agent)
    graph.add_node("await_gates", await_gates)
    graph.add_node("destroy_agent", destroy_agent)
    graph.add_node("audit_agent", audit_agent)

    graph.set_entry_point("delete_intake_agent")
    graph.add_edge("delete_intake_agent", "impact_agent")
    graph.add_conditional_edges("impact_agent", _route_impact, {"await_gates": "await_gates", END: END})
    graph.add_conditional_edges("await_gates", _route_gates, {"destroy_agent": "destroy_agent", END: END})
    graph.add_edge("destroy_agent", "audit_agent")
    graph.add_edge("audit_agent", END)

    return graph


def run_deletion(user_request: str) -> DeleteState:
    app = build_graph().compile()
    initial_state: DeleteState = {"user_request": user_request}
    return app.invoke(initial_state)


if __name__ == "__main__":
    request = " ".join(sys.argv[1:]).strip() or "Delete the EC2 instance prod-infra-ec2-api"
    result = run_deletion(request)
    print("[delete_graph] Completed with state keys:", sorted(result.keys()))
